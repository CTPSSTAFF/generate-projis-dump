PROJIS "Screen Scraper"
======================


The PROJIS "Screen Scraper" extracts information about all PROJIS projects
in the Boston MPO area currently in the PROJIS database, and writes it to an 
output CSV file. 

This tool has been placed into the directory:
\\lillput\groups\Certification_Activities\10103_Transportation Improvement Program\TIP Database\DatabaseInputs\PROJIS_Screen_Scraper

The main Python file is "generate_projis_dump.py"; the support library is 
"BeautifulSoup.py".

To run:
1. Open IDLE, then type
2. import generate_projis_dump
3. generate_projis_dump.generate_dump(output_file_name)

The output_file name parameter must be passed as a quoted string.
If "" is passed for the output_file_name parm, the output file defaults to 
"./projis_dump_<month>_<day>_<year>.csv", e.g., "./projis_dump_11_25_2009.csv".

No "input" parameter is required.

-- BK 12/08/09



