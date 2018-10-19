import os
import sys
from subprocess import call
import numpy as np
from cytomine import CytomineJob
from cytomine.models import Annotation, Job, ImageInstance, ImageGroupCollection, ImageSequenceCollection, AnnotationCollection,  Property
from shapely.affinity import affine_transform
from skimage import io

from annotation_exporter.mask_to_objects import mask_to_objects_3d
from neubiaswg5.metrics.compute_metrics import computemetrics_batch


def main(argv):
    # 0. Initialize Cytomine client and job
    with CytomineJob.from_cli(argv) as cj:
        cj.job.update(status=Job.RUNNING, progress=0, statusComment="Initialisation...")

        # 1. Create working directories on the machine:
        # - WORKING_PATH/in: input images
        # - WORKING_PATH/out: output images
        # - WORKING_PATH/ground_truth: ground truth images
        base_path = "{}".format(os.getenv("HOME"))
        gt_suffix = "_lbl"
        working_path = os.path.join(base_path, str(cj.job.id))
        in_path = os.path.join(working_path, "in")
        out_path = os.path.join(working_path, "out")
        gt_path = os.path.join(working_path, "ground_truth")

        if not os.path.exists(working_path):
            os.makedirs(working_path)
            os.makedirs(in_path)
            os.makedirs(out_path)
            os.makedirs(gt_path)

        # 2. Download the images (first input, then ground truth image)
        cj.job.update(progress=1, statusComment="Downloading images (to {})...".format(in_path))
        image_group = ImageGroupCollection().fetch_with_filter("project", cj.parameters.cytomine_id_project)

        input_images = [i for i in image_group if gt_suffix not in i.name]
        gt_images = [i for i in image_group if gt_suffix in i.name]

        for input_image in input_images:
            input_image.download(os.path.join(in_path, "{id}.tif"))

        for gt_image in gt_images:
            related_name = gt_image.name.replace(gt_suffix, '')
            related_image = [i for i in input_images if related_name == i.name]
            if len(related_image) == 1:
                gt_image.download(os.path.join(gt_path, "{}.tif".format(related_image[0].id)))

        # 3. Call the image analysis workflow using the run script
        cj.job.update(progress=25, statusComment="Launching workflow...")
        command = "/usr/bin/xvfb-run java -Xmx6000m -cp /fiji/jars/ij.jar ij.ImageJ --headless --console -macro macro.ijm \"input={}, output={}, radius={}, min_threshold={}\"".format(in_path, out_path, cj.parameters.ij_radius, cj.parameters.ij_min_threshold)
        return_code = call(command, shell=True, cwd="/fiji")  # waits for the subprocess to return

        if return_code != 0:
            err_desc = "Failed to execute the ImageJ macro (return code: {})".format(return_code)
            cj.job.update(progress=50, statusComment=err_desc)
            raise ValueError(err_desc)
            
        # 4. Upload the annotation and labels to Cytomine (annotations are extracted from the mask using
        # the AnnotationExporter module)    
        for image_group in cj.monitor(input_images, start=60, end=80, period=0.1, prefix="Extracting and uploading polygons from masks"):
            file = "{}.tif".format(image_group.id)
            path = os.path.join(out_path, file)
            data = io.imread(path)

            # extract objects
            objects = mask_to_objects_3d(np.moveaxis(data, 0, 2), background=0, assume_unique_labels=True)

            print("Found {} polygons in this image group {}.".format(len(objects), image_group.id))

            # create a structure mapping depth with image instance id
            image_sequences = ImageSequenceCollection().fetch_with_filter("imagegroup", image_group.id)
            depth_to_image = {iseq.zStack: iseq.image for iseq in image_sequences}
            height = ImageInstance().fetch(image_sequences[0].image).height
            
            # upload
            collection = AnnotationCollection()
            for object_slices in objects:
                for _slice in object_slices:
                    # TODO check why depth overflows
                    if _slice.depth not in depth_to_image:
                        print("problem with depth")
                        continue
                    collection.append(Annotation(
                        location=affine_transform(_slice.polygon, [1, 0, 0, -1, 0, height]).wkt,
                        id_image=depth_to_image[_slice.depth], id_project=cj.parameters.cytomine_id_project, property=[
                            {"key": "index", "value": str(_slice.label)}
                        ]
                    ))
            collection.save()

        # 5. Compute and upload the metrics
        cj.job.update(progress=80, statusComment="Computing and uploading metrics...")
        outfiles, reffiles = zip(*[
            (os.path.join(out_path, "{}.tif".format(image.id)),
             os.path.join(gt_path, "{}.tif".format(image.id)))
            for image in input_images
        ])
        results = computemetrics_batch(outfiles, reffiles, "ObjSeg", '/tmp')
        for key, value in results.items():
            Property(cj.job, key=key, value=str(value)).save()
        Property(cj.job, key="IMAGE_INSTANCES", value=str([im.id for im in input_images])).save()

        #Finished
        cj.job.update(status=Job.TERMINATED, progress=100, statusComment="Finished.")

        # TODO: compute metrics:
        # in /out: output files {id}.tiff
        # in /ground_truth: label files {id}.tiff
#        cj.job.update(progress=99, statusComment="Cleaning...")
#        for image in input_images:
#            os.remove(os.path.join(in_path, "{}.tif".format(image.id)))


if __name__ == "__main__":
    main(sys.argv[1:])

