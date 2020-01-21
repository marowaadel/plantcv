from __future__ import print_function
import os
import sys
import re
import json
from copy import deepcopy
import tempfile


# Build job list
###########################################
def job_builder(meta, config, workflow):
    """Build a list of image processing jobs.

    Args:
        meta:         Dictionary of processed image metadata.
        config:       plantcv.parallel.WorkflowConfig object.

    Returns:
        jobs:         List of image processing commands.

    :param meta: dict
    :param config: plantcv.parallel.WorkflowConfig
    :return job_stack: list
    """
    coprocess = None
    job_dir = tempfile.mkdtemp(dir=config.config["tmp_dir"])
    # Overall job stack. List of list of jobs
    jobs = []

    print("Job list will include " + str(len(meta)) + " images" + '\n', file=sys.stderr)

    # For each image group
    for group in meta:
        # For each image in the group
        for image in meta[group]:
            # Create a JSON template for the image
            img_meta = {"metadata": deepcopy(config.config["metadata_terms"]), "observations": {}}
            # Create an output file to store the image processing results and populate with metadata
            outfile = open(os.path.join(".", job_dir, img + ".txt"), 'w')
            # Store metadata in JSON
            img_meta["metadata"]["image"] = {
                    "label": "image file",
                    "datatype": "<class 'str'>",
                    "value": image["path"]
                }
        # Valid metadata
        for m in list(config.config["metadata_terms"].keys()):
            img_meta["metadata"][m]["value"] = meta[img][m]
        json.dump(img_meta, outfile)

        outfile.close()

        # Build job
        job_parts = ["python", workflow, "--image", os.path.join(meta[img]['path'], img),
                     "--outdir", config.config["output_dir"], "--result", os.path.join(job_dir, img) + ".txt"]
        # Add job to list
        if coprocess is not None and ('coimg' in meta[img]):
            job_parts = job_parts + ["--coresult", os.path.join(job_dir, meta[img]['coimg']) + ".txt"]
        if config.config["writeimg"]:
            job_parts.append("--writeimg")
        if config.config["other_args"]:
            other_args_copy = re.sub("'", "", config.config["other_args"])
            other_args_copy = other_args_copy.split(" ")
            job_parts = job_parts + other_args_copy
        jobs.append(job_parts)

    return jobs
###########################################
