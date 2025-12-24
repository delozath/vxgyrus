"""Single-file DICOM loader using pydicom.

Put here:
- read DICOM file
- extract pixel array (handle rescale slope/intercept)
- extract metadata tags (PatientID, StudyDate, etc.)
- return domain object (2D image wrapper or Volume with Z=1)
"""
