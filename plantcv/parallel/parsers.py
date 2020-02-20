import os
import re
import sys
import datetime


# Parse metadata from filenames in a directory
###########################################
def metadata_parser(config):
    """Image metadata parser.

    Inputs:
    config = plantcv.parallel.WorkflowConfig object

    Outputs:
    meta   = image metadata dictionary

    :param config: plantcv.parallel.WorkflowConfig
    :return meta: dict
    """
    # Metadata data structure
    meta = {}
    
    # A dictionary of metadata terms and their index position in the filename metadata term list
    metadata_index = {}
    for i, term in enumerate(config.config["filename_metadata"]):
        metadata_index[term] = i

    # How many metadata terms are in the files we intend to process?
    meta_count = len(config.config["filename_metadata"])

    # Compile regex (even if it's only a delimiter character)
    regex = re.compile(config.config["delimiter"])

    # Check whether there is a snapshot metadata file or not
    if os.path.exists(os.path.join(config.config["input_dir"], "SnapshotInfo.csv")):
        # Open the SnapshotInfo.csv file
        csvfile = open(os.path.join(config.config["input_dir"], 'SnapshotInfo.csv'), 'r')

        # Read the first header line
        header = csvfile.readline()
        header = header.rstrip('\n')

        # Remove whitespace from the field names
        header = header.replace(" ", "")

        # Table column order
        cols = header.split(',')
        colnames = {}
        for i, col in enumerate(cols):
            colnames[col] = i

        # Read through the CSV file
        for row in csvfile:
            row = row.rstrip('\n')
            data = row.split(',')
            img_list_str = data[colnames['tiles']]
            if img_list_str[:-1] == ';':
                img_list_str = img_list_str[:-1]
            img_list = img_list_str.split(';')
            for img in img_list:
                if len(img) != 0:
                    dirpath = os.path.join(config.config["input_dir"], 'snapshot' + data[colnames['id']])
                    filename = img + '.' + config.config["imgformat"]
                    if not os.path.exists(os.path.join(dirpath, filename)):
                        print("Something is wrong, file {0}/{1} does not exist".format(dirpath, filename),
                              file=sys.stderr)
                        continue
                        # raise IOError("Something is wrong, file {0}/{1} does not exist".format(dirpath, filename))
                    # Metadata from image file name
                    metadata = _parse_filename(filename=img, delimiter=config.config["delimiter"], regex=regex)
                    # Not all images in a directory may have the same metadata structure only keep those that do
                    if len(metadata) == meta_count:
                        # Image metadata
                        img_path = os.path.join(dirpath, filename)
                        img_meta = {}
                        img_pass = 1
                        # For each of the type of metadata PlantCV keeps track of
                        for term in config.config["metadata_terms"]:
                            # If the same metadata is found in the image filename, store the value
                            if term in metadata_index:
                                meta_value = metadata[metadata_index[term]]
                                # If the metadata type has a user-provided restriction
                                if term in config.config["metadata_filters"]:
                                    # If the input value does not match the image value, fail the image
                                    if meta_value != config.config["metadata_filters"][term]:
                                        img_pass = 0
                                img_meta[term] = meta_value
                            # If the same metadata is found in the CSV file, store the value
                            elif term in colnames:
                                meta_value = data[colnames[term]]
                                # If the metadata type has a user-provided restriction
                                if term in config.config["metadata_filters"]:
                                    # If the input value does not match the image value, fail the image
                                    if meta_value != config.config["metadata_filters"][term]:
                                        img_pass = 0
                                img_meta[term] = meta_value
                            # Or use the default value
                            else:
                                img_meta[term] = config.config["metadata_terms"][term]["value"]

                        if config.config["start_date"] and config.config["end_date"] and img_meta['timestamp'] is not None:
                            in_date_range = check_date_range(config.config["start_date"], config.config["end_date"], img_meta['timestamp'],
                                                             config.config["timestampformat"])
                            if in_date_range is False:
                                img_pass = 0

                        # If the image meets the user's criteria, store the metadata
                        if img_pass == 1:
                            if config.config["group_by"] is not None:
                                img_key = "_".join(map(str, [img_meta.get(term) for term in config.config["group_by"]]))
                            else:
                                img_key = filename
                            if img_key in meta:
                                meta[img_key][img_path] = img_meta
                            else:
                                meta[img_key] = {img_path: img_meta}
    else:
        # Compile regular expression to remove image file extensions
        pattern = re.escape('.') + config.config["imgformat"] + '$'
        ext = re.compile(pattern, re.IGNORECASE)

        # Walk through the input directory and find images that match input criteria
        for (dirpath, dirnames, filenames) in os.walk(config.config["input_dir"]):
            for filename in filenames:
                # Is filename and image?
                is_img = ext.search(filename)
                # If filename is an image, parse the metadata
                if is_img is not None:
                    # Remove the file extension
                    prefix = ext.sub('', filename)
                    metadata = _parse_filename(filename=prefix, delimiter=config.config["delimiter"], regex=regex)

                    # Not all images in a directory may have the same metadata structure only keep those that do
                    if len(metadata) == meta_count:
                        # Image metadata
                        img_path = os.path.join(dirpath, filename)
                        img_meta = {}
                        img_pass = 1
                        # For each of the type of metadata PlantCV keeps track of
                        for term in config.config["metadata_terms"]:
                            # If the same metadata is found in the image filename, store the value
                            if term in metadata_index:
                                meta_value = metadata[metadata_index[term]]
                                # If the metadata type has a user-provided restriction
                                if term in config.config["metadata_filters"]:
                                    # If the input value does not match the image value, fail the image
                                    if meta_value != config.config["metadata_filters"][term]:
                                        img_pass = 0
                                img_meta[term] = meta_value
                            # Or use the default value
                            else:
                                img_meta[term] = config.config["metadata_terms"][term]["value"]

                        if config.config["start_date"] and config.config["end_date"] and img_meta['timestamp'] is not None:
                            in_date_range = check_date_range(config.config["start_date"], config.config["end_date"], img_meta['timestamp'],
                                                             config.config["timestampformat"])
                            if in_date_range is False:
                                img_pass = 0

                        # If the image meets the user's criteria, store the metadata
                        if img_pass == 1:
                            if config.config["group_by"] is not None:
                                img_key = "_".join(map(str, [img_meta.get(term) for term in config.config["group_by"]]))
                            else:
                                img_key = filename
                            if img_key in meta:
                                meta[img_key][img_path] = img_meta
                            else:
                                meta[img_key] = {img_path: img_meta}

    return meta
###########################################


# Check to see if the image was taken between a specified date range
###########################################
def check_date_range(start_date, end_date, img_time, date_format):
    """Check image time versus included date range.

    Args:
        start_date: Start date in Unix time
        end_date:   End date in Unix time
        img_time:   Image datetime
        date_format: date format code for strptime

    :param start_date: int
    :param end_date: int
    :param img_time: str
    :param date_format: str
    :return: bool
    """

    # Convert image datetime to unix time
    try:
        timestamp = datetime.datetime.strptime(img_time, date_format)
    except ValueError as e:
        raise SystemExit(str(e) + '\n  --> Please specify the correct --timestampformat argument <--\n')
    
    time_delta = timestamp - datetime.datetime(1970, 1, 1)
    unix_time = (time_delta.days * 24 * 3600) + time_delta.seconds
    # Does the image date-time fall outside or inside the included range
    if unix_time < start_date or unix_time > end_date:
        return False
    else:
        return True
###########################################


# Filename metadata parser
###########################################
def _parse_filename(filename, delimiter, regex):
    """Parse the input filename and return a list of metadata.

    Args:
        filename:   Filename to parse metadata from
        delimiter:  Delimiter character to split the filename on
        regex:      Compiled regular expression pattern to process file with

    :param filename: str
    :param delimiter: str
    :param regex: re.Pattern
    :return metadata: list
    """

    # Split the filename on delimiter if it is a single character
    if len(delimiter) == 1:
        metadata = filename.split(delimiter)
    else:
        metadata = re.search(regex, filename)
        if metadata is not None:
            metadata = list(metadata.groups())
        else:
            metadata = []
    return metadata
###########################################
