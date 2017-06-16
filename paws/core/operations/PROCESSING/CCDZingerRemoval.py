"""
About
=====

cosmics.py is a small and simple python module to detect and clean cosmic ray hits on images (numpy arrays or FITS),
using scipy, and based on Pieter van Dokkum's L.A.Cosmic algorithm.

L.A.Cosmic = Laplacian cosmic ray detection

U{http://www.astro.yale.edu/dokkum/lacosmic/}

(article : U{http://arxiv.org/abs/astro-ph/0108003})


Additional features
===================

I pimped this a bit to suit my needs :

	- Automatic recognition of saturated stars, including their full saturation trails.
	This avoids that such stars are treated as big cosmics.
	Indeed saturated stars tend to get even uglier when you try to clean them. Plus they
	keep L.A.Cosmic iterations going on forever.
	This feature is mainly for pretty-image production. It is optional, requires one more parameter
	(a CCD saturation level in ADU), and uses some nicely robust morphology operations and object extraction.

	- Scipy image analysis allows to "label" the actual cosmic ray hits (i.e. group the pixels into local islands).
	A bit special, but I use this in the scope of visualizing a PSF construction.

But otherwise the core is really a 1-to-1 implementation of L.A.Cosmic, and uses the same parameters.
Only the conventions on how filters are applied at the image edges might be different.

No surprise, this python module is much faster then the IRAF implementation, as it does not read/write every step to disk.

Usage
=====

Everything is in the file cosmics.py, all you need to do is to import it. You need pyfits, numpy and scipy.
See the demo scripts for example usages (the second demo uses f2n.py to make pngs, and thus also needs PIL).

Your image should have clean borders, cut away prescan/overscan etc.



Todo
====
Ideas for future improvements :

	- Add something reliable to detect negative glitches (dust on CCD or small traps)
	- Top level functions to simply run all this on either numpy arrays or directly on FITS files
	- Reduce memory usage ... easy
	- Switch from signal to ndimage, homogenize mirror boundaries


Malte Tewes, January 2010
"""

import numpy as np
import scipy.signal as signal
import scipy.ndimage as ndimage
import time

from ..Operation import Operation
from .. import optools


# We define the laplacian kernel to be used
laplkernel = np.array([[0.0, -1.0, 0.0], [-1.0, 4.0, -1.0], [0.0, -1.0, 0.0]])


class CCDZingerRemoval(Operation):
    '''
    A routine for identifying zingers in CCD data.

    IMPORTANT:  This routine relies on (1) an accurate description of CCD properties and (2) an UNALTERED raw input
    image.  Subtracting any background or applying any scaling prior to this routine will wreak havoc with
    zinger detection.
    '''
#    def __init__(self, rawarray, gain=1.0, readnoise=0.0, satlevel=65536, pssl=0.0, sigclip=5.0, sigfrac=0.3,
#                 objlim=5.0, premask=np.zeros(1), verbose=True):
    def __init__(self):
        input_names = ['input_image','subtracted_background','pregenerated_mask','detector_params_dict',
                       'sigclip','sigfrac','objlim','verbose']
        output_names = ['q_I_bgsub', 'T_bg', 'bg_factor']
        super(CCDZingerRemoval, self).__init__(input_names, output_names)
        self.input_doc['input_image'] = 'The image from which you wish to remove zingers.'
        self.input_doc['detector_params_dict'] = str('Dictionary of detector properties as generated by '
        + 'CCDDetectorParameters; must contain values for readnoise, inverse_gain, and saturation_level')
        self.input_doc['pregenerated_mask'] = 'Known invalid regions and/or pixels; True/nonzero indicates bad pixel.'
        self.input_doc['sigclip'] = 'Increase this if you detect zingers where there is only noise.  Should be >=3.'
        self.input_doc['sigfrac'] = 'Increase if zingers "spread" too much.  Should be between 0 and 1.'
        self.input_doc['objlim'] = 'Increase this if normal features are detected as zingers.  Should be >=3.'
        self.input_doc['verbose'] = 'Turns on more detailed reporting.'
        # Source
        self.input_src['input_image'] = optools.wf_input
        self.input_src['detector_params_dict'] = optools.wf_input
        self.input_src['sigclip'] = optools.text_input
        self.input_src['sigfrac'] = optools.text_input
        self.input_src['objlim'] = optools.text_input
        self.input_src['verbose'] = optools.text_input
        # Type
        self.input_type['input_image'] = optools.ref_type
        self.input_type['detector_params_dict'] = optools.ref_type
        self.input_type['sigclip'] = optools.float_type
        self.input_type['sigfrac'] = optools.float_type
        self.input_type['objlim'] = optools.float_type
        self.input_type['verbose'] = optools.bool_type
        # Defaults
        self.inputs['subtracted_background'] = None
        self.inputs['pregenerated_mask'] = None
        self.inputs['sigclip'] = 5.0
        self.inputs['sigfrac'] = 0.5
        self.inputs['objlim'] = 5.0
        self.inputs['verbose'] = True
        """
        sigclip : laplacian-to-noise limit for cosmic ray detection
        objlim : minimum contrast between laplacian image and fine structure image. Use 5.0 if your image is undersampled, HST, ...

        saturation_level : if we find agglomerations of pixels above this level, we consider it to be a saturated star and
        do not try to correct and pixels around it. A negative saturation_level skips this feature.

        subtracted_background is the previously subtracted background !

        real   gain    = 1.8          # gain (electrons/ADU)	(0=unknown)
        real   readn   = 6.5		      # read noise (electrons) (0=unknown)
        ##gain0  string statsec = "*,*"       # section to use for automatic computation of gain
        real   skyval  = 0.           # sky level that has been subtracted (ADU)
        real   sigclip = 3.0          # detection limit for cosmic rays (sigma)
        real   sigfrac = 0.5          # fractional detection limit for neighbouring pixels
        real   objlim  = 3.0           # contrast limit between CR and underlying object
        int    niter   = 1            # maximum number of iterations

        """



    def second_init(self):
        inputs = self.inputs
        self.input_image = np.array(inputs['input_image'], dtype=float)
        if inputs['subtracted_background'] is not None: # internally, we work "with background"
            self.input_image += inputs['subtracted_background']

        self.cleanarray = self.input_image.copy()  # In lacosmiciteration() we work on this guy
        self.mask = np.zeros(self.input_image.shape, dtype=bool)  # All False, no cosmics yet # 0.000693 seconds
        if inputs['pregenerated_mask'] is not None:  # Optional pre-masked region
            self.pregenerated_mask = inputs['pregenerated_mask']
        else:
            self.pregenerated_mask = np.zeros(self.input_image.shape, dtype=bool)

        self.inverse_gain = float(inputs['detector_params_dict']['inverse_gain'])
        self.readnoise = float(inputs['detector_params_dict']['readnoise'])
        self.saturation_level = float(inputs['detector_params_dict']['saturation_level'])
        self.sigclip = inputs['sigclip']
        self.objlim = inputs['objlim']
        self.sigcliplow = inputs['sigclip'] * inputs['sigfrac']

        self.verbose = inputs['verbose']

        self.subtracted_background = inputs['subtracted_background']

        self.backgroundlevel = None  # only calculated and used if required.
        self.satstars = np.zeros(1, dtype=bool)  # a mask of the saturated stars, only calculated if required
        self.lastmask = np.zeros(1, dtype=bool)  # the previous version of self.mask, useful for finding changes
        self.med3 = np.zeros(1, dtype=float)
        self.med5 = np.zeros(1, dtype=float)
        self.med37 = np.zeros(1, dtype=float)


    def __str__(self):
        """
        Gives a summary of the current state, including the number of cosmic pixels in the mask etc.
        """
        stringlist = [
            "Input array : (%i, %i), %s" % (self.input_image.shape[0], self.input_image.shape[1], self.input_image.dtype.name),
            "Current cosmic ray mask : %i pixels" % np.sum(self.mask)
        ]

        if self.subtracted_background != 0.0:
            stringlist.append("Using a previously subtracted sky level of %f" % self.subtracted_background)

        if self.satstars.any():
            stringlist.append("Saturated star mask : %i pixels" % np.sum(self.satstars))

        return "\n".join(stringlist)

    def labelmask(self, verbose=None):
        """
        Finds and labels the cosmic "islands" and returns a list of dicts containing their positions.
        This is made on purpose for visualizations a la f2n.drawstarslist, but could be useful anyway.
        """
        if verbose == None:
            verbose = self.verbose
        if verbose:
            print "Labeling mask pixels ..."
            print "Elapsed time %f seconds." % (time.time() - self.t0)
        # We morphologicaly dilate the mask to generously connect "sparse" cosmics :
        dilmask = grow_four_directions(square_grow(self.mask, 1))
        # origin = 0 means center
        (labels, n) = ndimage.measurements.label(dilmask)
        slicecouplelist = ndimage.measurements.find_objects(labels)
        # Now we have a huge list of couples of numpy slice objects giving a frame around each object
        # For plotting purposes, we want to transform this into the center of each object.
        centers = [[(tup[0].start + tup[0].stop) / 2.0, (tup[1].start + tup[1].stop) / 2.0] for tup in slicecouplelist]
        # We also want to know how many pixels were affected by each cosmic ray.
        # Why ? Dunno... it's fun and available in scipy :-)
        sizes = ndimage.measurements.sum(self.mask.ravel(), labels.ravel(), np.arange(1, n + 1, 1))
        retdictlist = [{"name": "%i" % size, "x": center[0], "y": center[1]} for (size, center) in zip(sizes, centers)]

        if verbose:
            print "Labeling done"
            print "Elapsed time %f seconds." % (time.time() - self.t0)

        return retdictlist

    def getdilatedmask(self, size=3):
        """
        Returns a morphologically dilated copy of the current mask.
        size = 3 or 5 decides how to dilate.
        """
        if size == 3:
            dilmask = square_grow(self.mask, 1)
        elif size == 5:
            dilmask = grow_four_directions(square_grow(self.mask, 1))
        else:
            # dilmask = self.mask.copy()
            raise ValueError("Argument *size* of *getdilatedmask* should be either 3 or 5.")
        return dilmask

    def clean(self, mask=None, verbose=None):
        """
        Given the mask, we replace the actual problematic pixels with the masked 5x5 median value.
        This mimics what is done in L.A.Cosmic, but it's a bit harder to do in python, as there is no
        readymade masked median. So for now we do a loop...
        Saturated stars, if calculated, are also masked : they are not "cleaned", but their pixels are not
        used for the interpolation.

        We will directly change self.cleanimage. Instead of using the self.mask, you can supply your
        own mask as argument. This might be useful to apply this cleaning function iteratively.
        But for the true L.A.Cosmic, we don't use this, i.e. we use the full mask at each iteration.

        """
        if verbose == None:
            verbose = self.verbose
        if mask == None:
            mask = self.mask

        if verbose:
            print "Cleaning cosmic affected pixels ..."
            print "Elapsed time %f seconds." % (time.time() - self.t0)

        self.update_median_filters()
        self.cleanarray[mask] = self.med5[mask]
        # Generally, cleaning is done at this point.

        # This section will only trigger if there are masked regions larger than 5x5.
        infinite_entries = (np.isinf(self.cleanarray) & ~self.pregenerated_mask)
        median_size = 5
        while infinite_entries.any() and (median_size <= 9):
            # Tell user
            num_huge_cosmics = infinite_entries.sum()
            print '%i pixel(s) were in the middle of huuuuuuuuge cosmics.' % num_huge_cosmics
            print "Elapsed time %f seconds." % (time.time() - self.t0)
            # Employ alternative
            median_size += 2
            ignore_mask = self.mask & self.pregenerated_mask
            if self.satstars.any():
                ignore_mask = ignore_mask & self.satstars
            bigger_median = targeted_masked_median(self.input_image, infinite_entries, median_size, ignore_mask)
            self.cleanarray[infinite_entries] = bigger_median[infinite_entries]
            # See if any are left.
            infinite_entries = (np.isinf(self.cleanarray) & ~self.pregenerated_mask)

        if infinite_entries.any():  # If all else fails (masked regions larger than 9x9)
            backgroundlevel = self.guessbackgroundlevel()
            self.cleanarray[infinite_entries] = backgroundlevel

        if verbose:
            print "Cleaning done"
            print "Elapsed time %f seconds." % (time.time() - self.t0)

    def findsatstars(self, verbose=None):
        """
        Uses the saturation_level to find saturated stars (not cosmics !), and puts the result as a mask in self.satstars.
        This can then be used to avoid these regions in cosmic detection and cleaning procedures.
        Slow ...
        """
        if verbose == None:
            verbose = self.verbose
        if verbose:
            print "Detecting saturated features ..."
            print "Elapsed time %f seconds." % (time.time() - self.t0)
        # DETECTION

        satpixels = self.input_image > self.saturation_level  # the candidate pixels

        # We build a smoothed version of the image to look for large stars and their support :
        m5 = ndimage.filters.median_filter(self.input_image, size=5, mode='mirror')
        # We look where this is above half the saturation_level
        largestruct = m5 > (self.saturation_level / 2.0)
        # The rough locations of saturated stars are now :
        satstarscenters = np.logical_and(largestruct, satpixels)

        if verbose:
            print "Building mask of saturated features ..."
            print "Elapsed time %f seconds." % (time.time() - self.t0)

        # BUILDING THE MASK
        # The subtlety is that we want to include all saturated pixels connected to these saturated stars...
        # We dilate the satpixels alone, to ensure connectivity in glitchy regions and to add a safety margin around them.
        dilsatpixels = grow_four_directions(square_grow(satpixels, 1))


        # We label these :
        (dilsatlabels, nsat) = ndimage.measurements.label(dilsatpixels)

        if verbose:
            print "We have %i saturated features." % nsat
            print "Elapsed time %f seconds." % (time.time() - self.t0)

        # The ouput, False for now :
        outmask = np.zeros(self.input_image.shape)

        for i in range(1, nsat + 1):  # we go through the islands of saturated pixels
            thisisland = dilsatlabels == i  # gives us a boolean array
            # Does this intersect with satstarscenters ?
            overlap = np.logical_and(thisisland, satstarscenters)
            if np.sum(overlap) > 0:
                outmask = np.logical_or(outmask, thisisland)  # we add thisisland to the mask

        self.satstars = np.cast['bool'](outmask)

        if verbose:
            print "Mask of saturated features done"
            print "Elapsed time %f seconds." % (time.time() - self.t0)

    def getsatstars(self, verbose=None):
        """
        Returns the mask of saturated stars after finding them if not yet done.
        Intended mainly for external use.
        """
        if verbose == None:
            verbose = self.verbose
        if not self.saturation_level > 0:
            raise RuntimeError, "Cannot determine satstars : you gave saturation_level <= 0 !"
        if not self.satstars.any():
            self.findsatstars(verbose=verbose)
        return self.satstars

    def getmask(self):
        return self.mask

    def get_input_image(self):
        """
        For external use only, as it returns the input_image minus subtracted_background !
        """
        return self.input_image - self.subtracted_background

    def getcleanarray(self):
        """
        For external use only, as it returns the cleanarray minus subtracted_background !
        """
        return self.cleanarray - self.subtracted_background

    def guessbackgroundlevel(self):
        """
        Estimates the background level. This could be used to fill pixels in large cosmics.
        """
        if self.backgroundlevel == None:
            # self.backgroundlevel = np.median(self.input_image) # 0.071662902832 s
            self.backgroundlevel = np.median(self.input_image.ravel())  # 0.0666739940643 s
        return self.backgroundlevel

    ### whhhhaaat
    def positive_laplacian(self):
        # We subsample, convolve, clip negative values, and rebin to original size
        print "Beginning Laplacian calc: subsampling."
        print "Elapsed time %f seconds." % (time.time() - self.t0)
        subsampled = subsample(self.input_image)
        print "Laplacian calc: convolving."
        print "Elapsed time %f seconds." % (time.time() - self.t0)
        convolved = signal.convolve2d(subsampled, laplkernel, mode="same", boundary="symm")
        print "Laplacian calc:  clipping."
        print "Elapsed time %f seconds." % (time.time() - self.t0)
        clipped = convolved.clip(min=0.0)
        print "Laplacian calc: rebinning."
        print "Elapsed time %f seconds." % (time.time() - self.t0)
        lplus = rebin2x2(clipped)
        print "Laplacian calc done."
        print "Elapsed time %f seconds." % (time.time() - self.t0)
        return lplus

    def noise_model(self):
        # We build a custom noise map, so to compare the laplacian to
        # m5 = ndimage.filters.median_filter(self.cleanarray, size=5, mode='mirror')
        m5 = self.med5
        # We keep this m5, as I will use it later for the interpolation.
        m5clipped = m5.clip(min=0.0)  # As we will take the sqrt
        noise = (1.0 / self.inverse_gain) * np.sqrt(self.inverse_gain * m5clipped + self.readnoise * self.readnoise)
        return noise

    def create_median_filters(self):
        self.med3 = hybrid_masked_median(self.input_image, 3, self.pregenerated_mask)
        self.med5 = hybrid_masked_median(self.input_image, 5, self.pregenerated_mask)
        self.med37 = hybrid_masked_median(self.med3, 7, self.pregenerated_mask)

    def update_median_filters(self):
        ignore_mask = self.mask | self.pregenerated_mask
        if self.satstars.any():
            ignore_mask = ignore_mask | self.satstars
        fix_mask = (self.mask & (~self.pregenerated_mask))
        if self.satstars.any():
            fix_mask = (fix_mask & (~self.satstars))
        if self.lastmask.any():
            fix_mask = (fix_mask & (~self.lastmask))
        fix_mask_3 = grow_four_directions(fix_mask)
        med3update = targeted_masked_median(self.input_image, fix_mask_3, 3, ignore_mask)
        self.med3[fix_mask_3] = med3update[fix_mask_3]
        fix_mask_5 = grow_four_directions(fix_mask_3)
        med5update = targeted_masked_median(self.input_image, fix_mask_5, 5, ignore_mask)
        self.med5[fix_mask_5] = med5update[fix_mask_5]
        med37mask = np.isinf(self.med3) | self.pregenerated_mask  ### ?????
        self.med37 = hybrid_masked_median(self.med3, 7, med37mask)
        # Re-calculate areas near newly masked pixels
        # but not pre-masked areas

    def lacosmiciteration(self, verbose=None):
        """
        Performs one iteration of the L.A.Cosmic algorithm.
        It operates on self.cleanarray, and afterwards updates self.mask by adding the newly detected
        cosmics to the existing self.mask. Cleaning is not made automatically ! You have to call
        clean() after each iteration.
        This way you can run it several times in a row to to L.A.Cosmic "iterations".
        See function lacosmic, that mimics the full iterative L.A.Cosmic algorithm.

        Returns a dict containing
            - niter : the number of cosmic pixels detected in this iteration
            - nnew : among these, how many were not yet in the mask
            - itermask : the mask of pixels detected in this iteration
            - newmask : the pixels detected that were not yet in the mask

        If findsatstars() was called, we exclude these regions from the search.

        """

        if verbose == None:
            verbose = self.verbose

        if not self.med5.any():
            if verbose:
                print "Creating masked median filters..."
                print "Elapsed time %f seconds." % (time.time() - self.t0)
            self.create_median_filters()
        else:
            if verbose:
                print "Updating masked median filters..."
                print "Elapsed time %f seconds." % (time.time() - self.t0)
            self.update_median_filters()

        if verbose:
            print "Convolving image with Laplacian kernel ..."
            print "Elapsed time %f seconds." % (time.time() - self.t0)
        lplus = self.positive_laplacian()

        if verbose:
            print "Creating noise model ..."
            print "Elapsed time %f seconds." % (time.time() - self.t0)
        noise = self.noise_model()

        if verbose:
            print "Calculating Laplacian signal to noise ratio ..."
            print "Elapsed time %f seconds." % (time.time() - self.t0)
        sigmap = lplus / (2.0 * noise)  # the 2.0 is from the 2x2 subsampling
        # We remove the large structures (s prime) :
        s_prime = sigmap - hybrid_masked_median(sigmap, 5)  ## mask??

        if verbose:
            print "Selecting sharp-edged features as candidate cosmic rays ..."
            print "Elapsed time %f seconds." % (time.time() - self.t0)
        # Candidate cosmic rays (this will include stars + HII regions)
        candidates = s_prime > self.sigclip
        nbcandidates = np.sum(candidates)
        if verbose:
            print "  %5i candidate pixels" % nbcandidates
            print "Elapsed time %f seconds." % (time.time() - self.t0)

        # At this stage we use the saturated stars to mask the candidates, if available :
        if self.satstars.any():
            if verbose:
                print "Masking saturated stars ..."
                print "Elapsed time %f seconds." % (time.time() - self.t0)
            candidates = ((~self.satstars) & candidates)
            nbcandidates = np.sum(candidates)
            if verbose:
                print "  %5i candidate pixels not part of saturated stars" % nbcandidates
                print "Elapsed time %f seconds." % (time.time() - self.t0)

        if verbose:
            print "Building fine structure image ..."
            print "Elapsed time %f seconds." % (time.time() - self.t0)

        # We build the fine structure image :
        fine_structure = self.med3 - self.med37
        # In the article that's it, but in lacosmic.cl fine_structure is divided by the noise...
        # Ok I understand why, it depends on if you use s_prime/fine_structure or lplus/fine_structure as criterion.
        # s_prime, unlike lplus, has already been divided by noise once.
        # There are some differences between the article and the iraf implementation.
        # So I will stick to the iraf implementation.
        fine_structure = fine_structure / noise
        fine_structure = fine_structure.clip(min=0.0)  # as we will divide by f. like in the iraf version.

        if verbose:
            print "Removing suspected compact bright objects ..."
            print "Elapsed time %f seconds." % (time.time() - self.t0)
        # Now we have our better selection of cosmics :
        cosmics = (candidates & ((s_prime / fine_structure) > self.objlim))
        # Note the s_prime/fine_structure and not lplus/fine_structure ...
        # ... due to the fine_structure = fine_structure/noise above.

        nbcosmics = np.sum(cosmics)
        if verbose:
            print "  %5i remaining candidate pixels" % nbcosmics
            print "Elapsed time %f seconds." % (time.time() - self.t0)

        # What follows is a special treatment for neighbors of detected cosmics.
        # They are treated as more likely to be cosmics than the general population.
        if verbose:
            print "Finding neighboring pixels affected by cosmic rays ..."
            print "Elapsed time %f seconds." % (time.time() - self.t0)

        nbnew = int(nbcosmics)
        while (nbnew > 0):
            # We grow these cosmics to determine the immediate neighborhod  :
            growcosmics = square_grow(cosmics, 1)
            # From this grown set, we keep those that have s_prime > sigcliplow.
            # Note that the newly selected pixels did NOT meet both s_prime > self.sigclip and
            # (s_prime / fine_structure) > self.objlim), or they'd have been selected already.
            # Of these candidates, we require only the first condition, and that at a lower threshold.
            finalsel = (s_prime > self.sigcliplow) & growcosmics
            nbnew = (finalsel & (~cosmics)).sum() # The process repeats until it no longer IDs new pixels
            cosmics = (cosmics | finalsel) # New finds are folded back in
            if verbose:
                print "Neighborhood expansion iteration accomplished ..."
                print "Elapsed time %f seconds." % (time.time() - self.t0)
        finalsel = cosmics


        # Again, we have to kick out pixels on saturated stars :
        if self.satstars.any():
            if verbose:
                print "Masking saturated stars ..."
                print "Elapsed time %f seconds." % (time.time() - self.t0)
            finalsel = ((~self.satstars) & finalsel)

        nbfinal = np.sum(finalsel)
        if verbose:
            print "  %5i pixels detected as cosmics" % nbfinal
            print "Elapsed time %f seconds." % (time.time() - self.t0)

        # We find how many cosmics are not previously known :
        newmask = ((~self.mask) & finalsel)
        nbnew = np.sum(newmask)

        # We update the mask with the cosmics we have found :
        self.lastmask = self.mask.copy()
        self.mask = (self.mask | finalsel)

        # We return
        # (used by function lacosmic)

        return {"niter": nbfinal, "nnew": nbnew, "itermask": finalsel, "newmask": newmask}

    def run(self, maxiter=4, verbose=False):
        """
        Full artillery :-)
            - Find saturated stars
            - Run maxiter L.A.Cosmic iterations (stops if no more cosmics are found)

        Stops if no cosmics are found or if maxiter is reached.
        """
        self.t0 = time.time()
        self.second_init(self)

        if self.saturation_level > 0 and not self.satstars.any():
            self.findsatstars(verbose=True)

        print "Starting %i L.A.Cosmic iterations ..." % maxiter
        print "Elapsed time %f seconds." % (time.time() - self.t0)
        ii = 1
        nnew = np.nan
        while (ii <= maxiter) & (nnew != 0):
            print "Iteration %i" % ii
            iterres = self.lacosmiciteration(verbose=verbose)
            # iterres = {"niter": nbfinal,       # Number cosmics detected by this iteration
            #           "nnew": nbnew,          # Number cosmics not previously known
            #           "itermask": finalsel,   # Cosmics detected by this iteration
            #           "newmask": newmask}     # All known cosmics

            print "%i cosmic pixels (%i new)" % (iterres["niter"], iterres["nnew"])
            print "Elapsed time %f seconds." % (time.time() - self.t0)
            if iterres["nnew"] == 0:
                print "All detectable zingers have been identified."
            elif ii == maxiter:
                print "Maximum iterations preformed.  More zingers may remain."

            nnew = iterres["nnew"]
            ii += 1

        self.clean(verbose=verbose)
        # Note that for huge cosmics, one might want to revise this.
        # Thats why I added a feature to skip saturated stars !


# Array manipulation

def subsample(a):  # this is more a generic function than a method ...
    """
    Returns a 2x2-subsampled version of array a (no interpolation, just cutting pixels in 4).
    """
    big_a = np.zeros((a.shape[0] * 2, a.shape[1] * 2), a.dtype)
    big_a[::2, ::2] = a
    big_a[1::2, ::2] = a
    big_a[::2, 1::2] = a
    big_a[1::2, 1::2] = a
    return big_a


def rebin2x2(a):
    """
    Returns the average value of 2pix by 2pix regions.
    """
    h, w = a.shape
    if ((h / 2) * 2 != h) or ((w / 2) * 2 != w):
        raise ValueError("The input *a* to function *rebin2x2* must have an even number of columns and rows.")
    # new_a = np.zeros((h/2, w/2), dtype=a.dtype)
    new_a = (a[::2, ::2] + a[1::2, ::2] + a[::2, 1::2] + a[1::2, 1::2]) / 4.0
    return new_a


def targeted_masked_median(y, target_mask, n, legitimacy_mask):
    # Unlike hybrid_masked_median, the target mask must already be expanded if required
    # The medians will be evaluated from this padarray, skipping the np.inf.
    padarray = inf_padded_array(y, n)
    padarray[n:-n, n:-n][legitimacy_mask] = np.inf
    # Prep recipient array
    med = np.zeros(y.shape)  # 0.011280 seconds
    target_indices = np.argwhere(target_mask)
    for location in target_indices:
        ii, jj = location
        cutout = padarray[ii:(ii + 2 * n + 1), jj:(jj + 2 * n + 1)].ravel()  # remember the shift due to the padding !
        # Of our (2*n+1)**2 pixels, some of them are masked/np.inf and should be excluded
        goodcutout = cutout[cutout != np.inf]

        if np.size(goodcutout) > 0:
            replacementvalue = np.median(goodcutout)
        else:
            # i.e. no good pixels
            replacementvalue = np.inf
        med[ii, jj] = replacementvalue
    return med


def hybrid_masked_median(y, n, ignore_mask=np.zeros(1)):
    '''Combines maskless scipy median with true masked median for select areas.

    :param y:
    :param n:
    :param ignore_mask:
    :return:

    As the scipy ndimage.filters.median_filter routine is quite fast,
    it is used to initially calculate the median.  The median is then corrected
    to the masked-median value for edge regions and regions near masked pixels.

    This produces identical results to the full masked median,
    but in some cases this may represent a significant computation savings
    over directly applying the masked median to the full image.
    '''
    if (int(n) != ((int(n) / 2) * 2 + 1)) or (n < 0):
        raise ValueError("Argument *n* of *hybrid_masked_median* should be a positive odd whole number.")
    m = int(n) / 2  # 2*m + 1 = n

    # Make simple median
    med = ndimage.filters.median_filter(y, size=n, mode='mirror')

    # Re-calculate areas with edge effects and areas near pre-masked pixels
    edge_mask = edge_mask_array(y, m)
    if ignore_mask.any():
        pre_mask = square_grow(ignore_mask, m)
        fixit_mask = ((edge_mask | pre_mask) & ~ignore_mask)
    else:
        fixit_mask = edge_mask
    masked_median = targeted_masked_median(y, fixit_mask, n, fixit_mask)
    med[fixit_mask] = masked_median[fixit_mask]
    return med


def inf_padded_array(y, n):
    # Now we want to have a n pixel frame of Inf padding around our image.
    w, h = y.shape
    # padarray = np.zeros((w + 2*n, h + 2*n)) + np.inf
    padarray = np.zeros((w + 2 * n, h + 2 * n))
    padarray = padarray + np.inf
    padarray[n:-n, n:-n] = y.copy()  # copy to ensure no overwrite
    return padarray


def square_grow(mask, m):
    mask = mask.copy()
    for i in range(m):
        mask[:, 1:] = (mask[:, 1:] | mask[:, :-1])
        mask[:, :-1] = (mask[:, :-1] | mask[:, 1:])
    for i in range(m):
        mask[1:, :] = (mask[1:, :] | mask[:-1, :])
        mask[:-1, :] = (mask[:-1, :] | mask[1:, :])
    return mask


def grow_four_directions(mask):
    newmask = mask.copy()
    newmask[:, 1:] = (newmask[:, 1:] | mask[:, :-1])
    newmask[:, :-1] = (newmask[:, :-1] | mask[:, 1:])
    newmask[1:, :] = (newmask[1:, :] | mask[:-1, :])
    newmask[:-1, :] = (newmask[:-1, :] | mask[1:, :])
    return newmask


def edge_mask_array(y, m):
    edge_mask = np.zeros(y.shape, dtype=bool)
    edge_mask[:m, :] = True
    edge_mask[-m:, :] = True
    edge_mask[:, :m] = True
    edge_mask[:, -m:] = True
    return edge_mask
