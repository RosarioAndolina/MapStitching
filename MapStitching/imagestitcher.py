from matplotlib import pyplot as plt
import cv2 as cv

import numpy as np

from glob import glob
from os.path import join, exists, basename, splitext

from stitching.images import Images
from stitching.feature_detector import FeatureDetector
from stitching.feature_matcher import FeatureMatcher
from stitching.subsetter import Subsetter
from stitching.camera_estimator import CameraEstimator
from stitching.camera_adjuster import CameraAdjuster
from stitching.camera_wave_corrector import WaveCorrector
from stitching.warper import Warper
from stitching.cropper import Cropper
from stitching.blender import Blender
from stitching.seam_finder import SeamFinder
from stitching.exposure_error_compensator import ExposureErrorCompensator


class ImageStitcher():
    def __init__(self, images_list):
        
        self.finder = None
        self.matcher = None
        self.compensator = None
        self.subsetter = None
        self.features = None
        self.cameras = None
        self.keypoints = None
        self.matches = None
        self.load_and_resize_images(images_list)

    def load_and_resize_images(self, images_list = None):
        if images_list is not None:
            # self.images_list = load_images(images_list)
            self.images_list = images_list

        self.images = Images.of(self.images_list)
        
        if self.subsetter is not None:
            self.images.subset(self.indices)
            
        self.medium_imgs = list(self.images.resize(self.images.Resolution.MEDIUM))
        self.low_imgs = list(self.images.resize(self.images.Resolution.LOW))
        self.final_imgs = list(self.images.resize(self.images.Resolution.FINAL))

    def find_features(self):
        self.finder = FeatureDetector(detector='sift')
        self.features = [self.finder.detect_features(img) for img in self.medium_imgs]

    # def plot_keypoints(self, idx):
    #         if self.features is None: return
    #         keypoints = self.finder.draw_keypoints(self.medium_imgs[idx], self.features[idx])
    #         plot_image(keypoints, (15,20))

    def match(self):
        self.matcher = FeatureMatcher(matcher_type='affine')
        if self.features is None:
            self.find_features()
        
        # match
        self.matches = self.matcher.match_features(self.features)

        return self
        
    
    def subset(self, confidence_threshold = 1):
        self.subsetter = Subsetter(confidence_threshold=confidence_threshold    )
        if self.matches is None:
            raise RuntimeError('features not matched yet')
        
         # subset
        self.dot_notation = self.subsetter.get_matches_graph(self.images.names, self.matches)
        self.indices = self.subsetter.get_indices_to_keep(self.features, self.matches)

        self.medium_imgs = self.subsetter.subset_list(self.medium_imgs, self.indices)
        self.low_imgs = self.subsetter.subset_list(self.low_imgs, self.indices)
        self.final_imgs = self.subsetter.subset_list(self.final_imgs, self.indices)

        self.features = self.subsetter.subset_list(self.features, self.indices)
        self.matches = self.subsetter.subset_matches(self.matches, self.indices)
        
        self.images.subset(self.indices)

        return self

    def match_and_subset(self):
        self.match().subset()
        return self

    def print_confidence_matrix(self):
        if self.matches is None: return
        print(self.matcher.get_confidence_matrix(self.matches))

        return self

    # def plot_rilevant_matches(self, conf_thresh = None):
    #     for attribute in ['medium_imgs', 'features', 'matches']:
    #         if getattr(self, attribute) is None: return

    #     conf_thresh = conf_thresh if conf_thresh is not None else 1

    #     all_relevant_matches = self.matcher.draw_matches_matrix(
    #         self.medium_imgs,
    #         self.features,
    #         self.matches,
    #         conf_thresh=conf_thresh,
    #         inliers=True,
    #         matchColor=(0, 255, 0)
    #     )

    #     for idx1, idx2, img in all_relevant_matches:
    #         print(f"Matches Image {idx1+1} to Image {idx2+1}")
    #         plot_image(img, (10,5))

        return self

    def print_corrispondences(self):
        if self.dot_notation is None: return
        print(self.dot_notation)

        return self

    def prepare_cameras(self):

        if self.features is None: return

        camera_estimator = CameraEstimator(estimator='affine')
        camera_adjuster = CameraAdjuster(adjuster='affine')
        wave_corrector = WaveCorrector(wave_correct_kind='no')

        self.cameras = camera_estimator.estimate(self.features, self.matches)
        self.cameras = camera_adjuster.adjust(self.features, self.matches, self.cameras)
        self.cameras = wave_corrector.correct(self.cameras)

        return self

    def _warp_low_resolution(self):

        if self.cameras is None: return
        
        self.low_sizes = self.images.get_scaled_img_sizes(self.images.Resolution.LOW)
        self.camera_aspect = self.images.get_ratio(self.images.Resolution.MEDIUM, self.images.Resolution.LOW)

        # warp
        self.warped_low_imgs = list(self.warper.warp_images(self.low_imgs, self.cameras, self.camera_aspect))
        self.warped_low_masks = list(self.warper.create_and_warp_masks(self.low_sizes, self.cameras, self.camera_aspect))
        self.low_corners, self.low_sizes = self.warper.warp_rois(self.low_sizes, self.cameras, self.camera_aspect)

        return self

    def _warp_final_resolution(self):

        if self.cameras is None: return
        
        self.final_sizes = self.images.get_scaled_img_sizes(self.images.Resolution.FINAL)
        self.camera_aspect = self.images.get_ratio(self.images.Resolution.MEDIUM, self.images.Resolution.FINAL)

        # warp
        self.warped_final_imgs = list(self.warper.warp_images(self.final_imgs, self.cameras, self.camera_aspect))
        self.warped_final_masks = list(self.warper.create_and_warp_masks(self.final_sizes, self.cameras, self.camera_aspect))
        self.final_corners, self.final_sizes = self.warper.warp_rois(self.final_sizes, self.cameras, self.camera_aspect)

        return self

    def warp_images(self):
        
        if self.features is None: return
        if self.cameras  is None: return

        self.load_and_resize_images()

        self.warper = Warper(warper_type='affine')
        self.warper.set_scale(self.cameras)

        self._warp_low_resolution()

        self._warp_final_resolution()

        return self

    def crop_images(self):

        self.cropper = Cropper()

        self.cropper.prepare(self.warped_low_imgs, self.warped_low_masks, self.low_corners, self.low_sizes)

        # crop low images and masks
        self.cropped_low_masks = list(self.cropper.crop_images(self.warped_low_masks))
        self.cropped_low_imgs = list(self.cropper.crop_images(self.warped_low_imgs))
        self.low_corners, self.low_sizes = self.cropper.crop_rois(self.low_corners, self.low_sizes)

        # crop final images and masks
        self.lir_aspect = self.images.get_ratio(self.images.Resolution.LOW, self.images.Resolution.FINAL)
        self.cropped_final_masks = list(self.cropper.crop_images(self.warped_final_masks, self.lir_aspect))
        self.cropped_final_imgs = list(self.cropper.crop_images(self.warped_final_imgs, self.lir_aspect))
        self.final_corners, self.final_sizes = self.cropper.crop_rois(self.final_corners, self.final_sizes, self.lir_aspect)

        # find seam masks
        self.find_seam_masks()

        return self

    # def plot_mask(self):
    #     if not hasattr(self, 'lir'): return
    #     plot = self.lir.draw_on(self.mask, size = 2)
    #     plot_image(plot, (5,5))
    #     return self

    def find_seam_masks(self):
        seam_finder = SeamFinder()
        self.seam_masks = seam_finder.find(self.cropped_low_imgs, self.low_corners, self.cropped_low_masks)
        self.seam_masks = [seam_finder.resize(seam_mask,mask) for seam_mask, mask in zip(self.seam_masks, self.cropped_final_masks)]

        return self

    # def plot_seam_masks(self):
    #     seam_mask_plot = [SeamFinder.draw_seam_mask(img, seam_mask) for img, seam_mask in zip(self.cropped_final_imgs, self.seam_masks)]
    #     plot_images(seam_mask_plot, (10,20))

    #     return self

    def compensate(self):
        if hasattr(self, "warped_low_imgs"):
            compensator = ExposureErrorCompensator()
            compensator.feed(self.low_corners, self.warped_low_imgs, self.warped_low_masks)
            self.compensated_imgs = [
                compensator.apply(idx, corner, img, mask)
                for idx, (img, mask, corner)
                in enumerate(zip(self.warped_final_imgs, self.warped_final_masks, self.final_corners))
            ]
        return self

    def blend(self, images_list = None, crop = True):
        if images_list is not None:
            self.load_and_resize_images(images_list)
            self._warp_final_resolution()

            self.compensate()
        
            if crop:
                # self.cropped_final_masks = list(self.cropper.crop_images(self.warped_final_masks, self.lir_aspect))
                # self.cropped_final_imgs = list(self.cropper.crop_images(self.warped_final_imgs, self.lir_aspect))
                self.cropped_final_masks = list(self.cropper.crop_images(self.warped_final_masks, self.lir_aspect))
                self.cropped_final_imgs = list(self.cropper.crop_images(self.compensated_imgs, self.lir_aspect))
                self.final_corners, self.final_sizes = self.cropper.crop_rois(self.final_corners, self.final_sizes, self.lir_aspect)

        final_imgs = self.cropped_final_imgs if crop else self.compensated_imgs
        final_masks = self.seam_masks if crop else self.warped_final_masks

        # blend images
        blender = Blender()
        blender.prepare(self.final_corners, self.final_sizes)
        for img, mask, corner in zip(final_imgs, final_masks, self.final_corners):
            blender.feed(img, mask, corner)
        panorama, _ = blender.blend()
        return panorama