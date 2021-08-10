## Read dataset

This function reads a dataset of images as a list of paths.

**plantcv.io.read_dataset**(*source_path, pattern=''*)

**returns** image_dataset

- **Parameters:**
    - source_path - Path to the directory of images
    - pattern     - Optional, the function returns only the paths where the filename contains the pattern.


- **Context:**
    - This function is useful when it is required to read a set of images containing a given pattern.


- **Example use:**

```python
from plantcv import plantcv as pcv

image_dataset = pcv.io.read_dataset(source_path='./data/', pattern='color')

```
