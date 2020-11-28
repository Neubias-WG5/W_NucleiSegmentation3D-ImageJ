import sys
from subprocess import call

from cytomine.models import Job

from biaflows import CLASS_OBJSEG
from biaflows.helpers import BiaflowsJob, prepare_data, upload_data, upload_metrics


def main(argv):
    # 0. Initialize Cytomine client and job
    with BiaflowsJob.from_cli(argv) as nj:
        nj.job.update(status=Job.RUNNING, progress=0, statusComment="Initialisation...")

        problem_cls = CLASS_OBJSEG
        is_2d = False

        # 1. Create working directories on the machine
        # 2. Download the images
        in_images, gt_images, in_path, gt_path, out_path, tmp_path = prepare_data(problem_cls, nj, is_2d=is_2d, **nj.flags)

        # 3. Call the image analysis workflow using the run script
        nj.job.update(progress=25, statusComment="Launching workflow...")
        command = "/usr/bin/xvfb-run java -Xmx6000m -cp /fiji/jars/ij.jar ij.ImageJ --headless --console " \
                  "-macro macro.ijm \"input={}, output={}, radius={}, min_threshold={}\"".format(in_path, out_path, nj.parameters.ij_radius, nj.parameters.ij_min_threshold)
        return_code = call(command, shell=True, cwd="/fiji")  # waits for the subprocess to return

        if return_code != 0:
            err_desc = "Failed to execute the ImageJ macro (return code: {})".format(return_code)
            nj.job.update(progress=50, statusComment=err_desc)
            raise ValueError(err_desc)
            
        # 4. Upload the annotation and labels to Cytomine (annotations are extracted from the mask using
        # the AnnotationExporter module)
        upload_data(problem_cls, nj, in_images, out_path, **nj.flags, is_2d=is_2d, monitor_params={
            "start": 60, "end": 90,
            "period": 0.1,
            "prefix": "Extracting and uploading polygons from masks"
        })

        # 5. Compute and upload the metrics
        nj.job.update(progress=80, statusComment="Computing and uploading metrics (if necessary)...")
        upload_metrics(problem_cls, nj, in_images, gt_path, out_path, tmp_path, **nj.flags)

        nj.job.update(status=Job.TERMINATED, progress=100, statusComment="Finished.")


if __name__ == "__main__":
    main(sys.argv[1:])
