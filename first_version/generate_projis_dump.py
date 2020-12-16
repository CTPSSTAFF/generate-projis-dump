"""
Module: generate_projis_dump
INPUT:  An HTML file containing the HTML from the MassDOT "PROJIS" web page for a list of projects.
        This is typically all the projects in the Boston MPO area.
OUTPUT: A CSV file, each record of which contains the attributes for one PROJIS project, extracted
        from the top-level HTML file as well as the HTML for the page containing detailed information
        for each project.
This module uses the BeautifulSoup library to handle reading, parsing, searching, etc. of the HTML.
BeautifulSoup is able to handle reading/parsing of mal-formed (as well-formed) HTML w/o crashing.
However, in cases where the input HTML is mal-formed, the ability of BeautifulSoup to search/navigate
the HTML is somewhat limited. There is at least one such case in the PROJIS HTML (see in-line comments,
below). In this case, we search/navigate through the HTML in question as raw text.

For information and documentation, see http://www.crummy.com/software/BeautifulSoup/
BeautifulSoup was written by Leonard Richardson (leonardr@segfault.org).
This application was originally developed using BeautifulSoup version 3.1.0.1.

A note for dyed-in the-wool Pythonistas: The code for this module is written in an admittedly
very conservative style, and as such cannot be regarded as particulalry idiomatic Python.
Some of this (e.g., the use of many variables to hold temporary, intermediate results) is a
consequence of much of the code having been developed through prototyping and experimentation.
Because no documentation exists for the structure of the HTML for the PROJIS pages, it was
necessary to determine this structre by "poking around" in the data structure returned by
BeautifulSoup and correlating what was found this way with what was found when exploring
the raw HTML with a text editor. Wasn't it Descartes who said, "Hackito, ergo sum"?
If not, maybe it was Moe Howard.

Other non-idomatic qualities of the code are due to Your Humble Author's great distaste for
a programming language that treats white space (indentation, in particular) as a syntactically
signifcant element. As someone who has (among other things) designed programming languages
professionally, Your Humble Author can say with confidence that this is poor language design,
pure and simple (regardless of how much it may facilitate hacking).
White space, first and foremost, is DOCUMENTATION. Harrumph!

-- BK (founding member, Union of Concerned Curmudgeons) 11/25/2009
"""

from BeautifulSoup import BeautifulSoup
import re
import urllib2
import datetime

# Some symbolic constants:
newline = "\n"
comma = ','


# The following are currently not used:
# 1. The URLs for individual projects appear to always be correct in the HTML
#    generated for a list of projects in a given MPO, etc.
# 2. We currently don't access the URL for individual bridges.
# I'm keeping these around, however, in case they may come in handy in the future.
base_project_url = "http://www.mhd.state.ma.us/ProjectInfo/Main.asp?ACTION=ViewProject&PROJECT_NO="
base_bridge_url = "http://www.mhd.state.ma.us/ProjectInfo/Main.asp?ACTION=BridgeInfo&BRIDGE_NO="

# Number of times exception handler in process_project is called.
num_exceptions = 0


# The project description string and some other strings extracted from the HTML
# require some special processing, as it may contain various kinds of crud:
#     1. &amp; (and perhaps other web-crud) - for now, we just deal with &amp;
#     2. \n
#     3. \r
# This function is also serves as a placeholder where other string-cleanup
# logic that may be needed in the future can be placed.
# This function cleans up the raw input string so that it may be stored
# as an ASCII string in a CSV (i.e., comma delimited) text file. As such,
# the entire "cleaned up" version of the string is enclosed in double-quotes.
# This is necessary, as the input string may contain commas, which would
# otherwise be regarded as delimiters in the CSV otuput file.
#
# The "cleaned up" and double-quote delimited version of the input string
# is the return value of this function.
def cleanup_string(input_string):
        tmp1 = input_string.replace('&amp;','&')
        tmp2 = tmp1.replace('\n',' ')
        tmp3 = tmp2.replace('\r', ' ')
        tmp4 =  "\"" + tmp3 + "\""
        # print str(len(tmp4)) + " " + tmp4
        return tmp4
# end_def (of cleanup_string)

# Get the Right of Way Certification Issued Date for the project, if present.
#
# Note: Although a label for this field is usually present in the HTML,
#       a corresponding value is often absent. Due to the way the HTML
#       is strucutred, detecting this has proven exceptionally difficult.
#
# IF PRESENT, the HTML table containing the ROW certification date
#             is given by:
#                 row_th.parent.parent.contents[3].
#             The HTML table cell containing the ROW certification
#             date itself is given by:
#                 row_th.parent.parent.contents[3].contents[5].string
#
# However, things can be pretty tangled here, and if the HTML is not
# organized as expected, an exception will be raised, and we return ' '.
#
# Parameters: proj_soup - the BeautifulSoup for the project page       
#             proj_dict - the dictionary being assembled for the project (IN/OUT)
#
def get_row_cert_issued_date(proj_soup, proj_dict):
        try:
                row_cert_issued_date = ' '
                ths = proj_soup.findAll("th", { "class" : "sectionHeader2" })
                if (len(ths) != 0):
                        found_row_th = 0
                        for this_th in ths:
                                if (this_th.string == "Right of Way"):
                                        row_th = this_th
                                        found_row_th = 1
                                        break
                                # end_if
                        # end_for
                        if (found_row_th == 1):
                                if (len(row_th.parent.parent.contents) >= 3):
                                        if (len(row_th.parent.parent.contents[3].contents) >= 5):
                                                row_cert_issued_date = row_th.parent.parent.contents[3].contents[5].string
                                        # end_if
                                # end_if
                        # end_if
                # end_if 
                # print "ROW cert issued date is: " + row_cert_issued_date
                return row_cert_issued_date
        except:
                return ' '
# end_def (of get_row_cert_issued_date)


def process_project(proj_num, proj_url, proj_dict):
        """
        Process the data for a single PROJIS project, stored in one web page.
        Parameters:
        proj_num  - project number
                    This parm, strictly speaking, isn't needed.
                    It's here only to facilitate generation of
                     trace/debug output within this routine.
        proj_url  - the URL of the web page for a PROJIS project.
        proj_dict - dictionary in which the values of the desired
                    database fields for this project are stored.
                    Note: this is an in/out parameter.
        Return value:  none
        Note that the body of this routine is enclosed in one huge try/except block.
        If there are any errors when attempting to extract the attribute data for
        an individual project, this routine "bails", returning blank strings for
        the values of all keys in the in/out-parm "proj_dict".
        """
        global num_exceptions
        # Trace/debug output
        print "Processing project: " + proj_num
        # print "    URL: " + proj.contents[1].contents[0]["href"]
        try:
                proj_page = urllib2.urlopen(proj_url)
                proj_soup = BeautifulSoup(proj_page)
        
                # Towns (a.k.a. "Jurisdictions for this Project").
                #
                # Note: Navigation here is not simple.
                # The HTML here is layed out as follows:
                #
                # <tr> - This is the parent node.
                # <td class="attrName" title="Jurisdiction(s) for this Project" id="LOC"> Location:
                # </td>
                # <td class="attrValue">                       *** NOTE: This is parent.contents[3]
                #     <li> <a blah...> Town of XXX </a> </li>
                #     <li> <a blah...> City of YYY </a> </li>
                #     etc.
                # </td>
                # </tr>
                #
                # That is to say, the <li>'s for the towns/cities are NOT enclosed
                # within a <ul> ... </ul> pair. I.e., the HTML is MAL-FORMED!!!
                #
                # Although the HTML is malformed, BeautifulSoup is able to parse/load it.
                # However, because the HTML is malformed, we cannot navigate around it
                # as though it were properly formed (i.e., BeautifulSoup does NOT insert
                # the required <ul> and </ul> nodes ... we have to grovel around a bit.
                #
                # Given the <td> node with id="LOC" (and class="attrName"), let P be its parent.
                # Then:
                #    1. P.contents[3] is the <td> with class="attrValue"; let this be X.
                #    2. The EVEN numbered contents of X are the <li>'s with the names of the towns.
                # However, because the HTML is malformed, these <li>'s don't behave like "real" <li>'s,
                # we can't get their contents by saying li_node.contents[0] or even li_node.string.
                # (Both of these cause BeautifulSoup to crash.) What we wind up having to do is grovel
                # through the pseudo-<li>'s as though they were strings.
                # BECAUSE OF THIS, THE CODE HERE IS VERY FRAGILE AND VULNERABLE TO BREAKAGE IF THE
                # STRUCTURE OF THE INPUT HTML IS CHANGED.
                # Them's the breaks.

                cur_attr = "Towns"
                tds = proj_soup.findAll("td", id="LOC")
                temp_towns_str = ' '
                if (tds):
                        parent = tds[0].parent
                        node = parent.contents[3]
                        j = 0
                        for subnode in node.contents:
                                j = j + 1
                                if (j % 2 == 0):
                                        tmp1 = str(subnode.contents)
                                        start_ix = tmp1.find('">') + 2 
                                        end_ix = tmp1.find('</a')
                                        tmp2 = tmp1[start_ix:end_ix]
                                        tmp3 = tmp2.replace('City of ','')
                                        tmp4 = tmp3.replace('Town of ','')
                                        temp_towns_str = temp_towns_str + ' ' + tmp4
                                # end_if
                        # end_for
                # end_if
                towns_str = temp_towns_str.lstrip() if (len(temp_towns_str) > 1) else ' '
                proj_dict['TOWNS'] = towns_str
        
                # (Long) Project Description
                #
                cur_attr = "Long Project Description"
                tds = proj_soup.findAll("td", id="PROJ_DESC")
                # The following line retreives the desired value.
                # Note: this has to be "cleaned up", as was the case for the short description.
                if (len(tds[0].nextSibling.nextSibling.contents) >= 1):
                        t1 = cleanup_string(tds[0].nextSibling.nextSibling.contents[1].string)
                else:
                        t1 = ' '
                # end_if
                # print t1
                proj_dict['LONG_DESC'] = t1

                # Construction Begins
                #
                cur_att = "Construction Begins"
                tds = proj_soup.findAll("td", id="CON_BEGINS")
                if (len(tds) != 0):
                        # The following line retreives the desired value.
                        t1 = tds[0].nextSibling.nextSibling.string
                else:
                        t1 = ' '
                # end_if
                proj_dict['CON_BEGINS'] = t1

                # Construction Ends
                #
                cur_attr = "Construction Ends"
                tds = proj_soup.findAll("td", id="CON_ENDS")
                if (len(tds) != 0):
                        # The following line retreives the desired value.
                        t1 = tds[0].nextSibling.nextSibling.string
                else:
                        t1 = ' '
                # end_if
                proj_dict['CON_ENDS'] = t1

                # Resident Engineer
                #
                cur_attr = "Resident Engineer"
                tds = proj_soup.findAll("td", id="RES_ENGR")
                if (len(tds) != 0):
                        # The following line retreives the desired value.
                        t1 = tds[0].nextSibling.nextSibling.contents[0].string
                        # Have to clean up possible commas in this value, e.g., "John Doe, III".
                        t2 = t1.replace(',',' ')
                else:
                        t2 = ' '
                # end_if
                proj_dict['RES_ENGR'] = t2

                # MHD District
                #
                cur_attr = "MHD District"
                tds = proj_soup.findAll("td", id="MHD_DIST")
                if (len(tds) != 0):
                        # The following line retreives the desired value.
                        t1 = tds[0].nextSibling.nextSibling.string
                else:
                        t1 = ' '
                # end_if
                proj_dict['MHD_DIST'] = t1

                # Current Status
                # Ugh. This field may also need some cleaning up...
                #
                cur_attr = "Current Status"
                tds = proj_soup.findAll("td", id="CUR_STATUS")
                if (len(tds) != 0):
                        # The following line retreives the desired value.
                        t1 = tds[0].nextSibling.nextSibling.string
                        if (t1):
                                t2 = cleanup_string(tds[0].nextSibling.nextSibling.string)
                        else:
                                t2 = ' '
                        # end_if
                else:
                        t2 = ' '
                # end_if
                proj_dict['CUR_STATUS'] = t2

                # Bridges
                #
                # Note: There may be 0 to N (N >= 1) bridges associated with a project.
                # This is currently anchored in the only <h4> tag in the project page.
                # But we take precautions in case other <h4> tags are added in the future.
                cur_attr = "Bridges"
                h4s = proj_soup.findAll("h4")
                found_bridge_h4 = 0
                for this_h4 in h4s:
                        if (this_h4.string == "Bridges"):
                                bridge_h4 = this_h4
                                found_bridge_h4 = 1
                                break
                        # end_if
                # end_for
                #
                # bridge_h4.nextSibling.nextSibling gets us to the <ul> for the list of bridges.
                # The odd-numbered elements of this <ul> the actual bridge numbers.
                temp_bridges_str = ' '
                if (found_bridge_h4 == 1):
                        i = 0 
                        for li_node in bridge_h4.nextSibling.nextSibling.contents:
                                if (i % 2 == 1):
                                        # The contents of the <li> node can contain various kinsd of crud,
                                        # including '\r' and a lot of leading/trailing spaces.
                                        # Clean this up.
                                        t1 = li_node.contents[0]
                                        t2 = t1.replace('\n','')
                                        t3 = t2.replace('\r','')
                                        t4 = t3.lstrip()
                                        t5 = t4.rstrip()
                                        temp_bridges_str = temp_bridges_str + ' ' + t5
                                # end_if
                                i = i + 1
                        # end_for
                # end_if
                bridges_str = temp_bridges_str.lstrip() if (len(temp_bridges_str) > 1) else ' ' 
                proj_dict['BRIDGES'] = bridges_str

                # Design responsibility
                #
                cur_attr = "Design Responsibility"
                tds = proj_soup.findAll("td", id="DES_RESP")
                if (len(tds) != 0):
                        # The following line retreives the desired value.
                        t1 = tds[0].nextSibling.nextSibling.string
                else:
                        t1 = ' '
                # end_if
                proj_dict['DES_RESP'] = t1


                # Right-of-Way responsibility
                #
                cur_attr = "ROW Responsibility"
                tds = proj_soup.findAll("td", id="RIGHT_OF_WAY")
                if (len(tds) != 0):
                        # The following line retreives the desired value.
                        t1 = tds[0].nextSibling.nextSibling.string
                else:
                        t1 = ' '
                # end_if
                proj_dict['ROW_RESP'] = t1


                # Date right-of-way certification issued
                #
                # Note: Although a label for this field is usually present in the HTML,
                #       a corresponding value is often absent. Due to the way the HTML
                #       is strucutred, detecting this has proven quite difficult and
                #       error-prone.
                #       In order to avoid triggering the exception handler here, and
                #       blowing away all the detailed project attributes in that case,
                #       we shunt the processing here off to a subroutine.
                #
                cur_attr = "ROW Certification Issued Date"
                row_cert_issued_date = get_row_cert_issued_date(proj_soup, proj_dict)
                proj_dict['ROW_CERT_ISSUED'] =  row_cert_issued_date


                # Estimated construction cost
                #
                cur_attr = "Estimated Construction Cost"
                tds = proj_soup.findAll("td", id="EST_CON_COST")
                if (len(tds) != 0):
                        # The following line retreives the desired value.
                        t1 = tds[0].nextSibling.nextSibling.contents[0].contents[0].string
                        # Remove dollar sign and commas from this string.
                        t2 = t1.replace('$','')
                        t3 = t2.replace(',','')
                else:
                        t3 = ' '
                # end_if
                proj_dict['EST_CON_COST'] = t3
                

                # Date PRC approved
                #
                cur_attr = "PRC Approved Date"
                tds = proj_soup.findAll("td", title="Approved")
                if (len(tds) != 0):
                        # The following line retreives the desired value.
                        t1 = tds[0].nextSibling.nextSibling.string
                else:
                        t1 = ' '
                # end_if
                proj_dict['DATE_PRC_APPROVED'] =  t1

                # Date 25% submitted
                #
                cur_attr = "Date 25% Submitted"
                tds = proj_soup.findAll("td", title="The 25% project plan has been submitted to MassHighway for review and comment.")
                if (len(tds) != 0):
                        # The following line retreives the desired value.
                        t1 = tds[0].nextSibling.nextSibling.string
                else:
                        t1 = ' '
                proj_dict['DATE_25_SUBMITTED'] =  t1

                # Date 75% submitted
                #
                cur_attr = "Date 75% Submitted"
                tds = proj_soup.findAll("td", title="The 75% project plan has been submitted to MassHighway for review and comment.")
                if (len(tds) != 0):
                        # The following line retreives the desired value.
                        t1 = tds[0].nextSibling.nextSibling.string
                else:
                        t1 = ' '
                proj_dict['DATE_75_SUBMITTED'] =  t1

                # Date 100% submitted
                #
                cur_attr = "Date 100% Submitted"
                tds = proj_soup.findAll("td", title="The final project plan has been submitted to MassHighway for review and comment.")
                if (len(tds) != 0):
                        # The following line retreives the desired value.
                        t1 = tds[0].nextSibling.nextSibling.string
                else:
                        t1 = ' '
                proj_dict['DATE_100_SUBMITTED'] =  t1

                # Date PSE submitted
                #
                # This is ticky. The title attribute of the <td> node we're looking for is:
                #     "Plans, Specifications and Estimate have been received for final review"
                # However, BeautifulSoup has problems searching for attributes containing a comma.
                # So, we have to search for this node in a bit more brute-force way.
                #
                cur_attr = "Date PSE Submitted"
                tds = proj_soup.findAll("td", { "class" : "attrName" })
                if (len(tds) != 0):
                        found_pse_sub_td = 0
                        for this_td in tds:
                                if (this_td.string == "PS&amp;E Received"):
                                        pse_sub_td = this_td
                                        found_pse_sub_td = 1
                                        break
                                # end_if
                        # end_for
                        if (found_pse_sub_td == 1):
                                t1 = pse_sub_td.nextSibling.nextSibling.string
                        else:
                                t1 = ' '
                        # end_if
                else:
                        t1 = ' '
                # end_if
                proj_dict['DATE_PSE_SUBMITTED'] =  t1
                
        except:
                print "Entering exception handler. Attribute currently being processed is: " + cur_attr
                num_exceptions = num_exceptions + 1
                proj_dict['TOWNS'] = ' '
                proj_dict['LONG_DESC'] = ' '
                proj_dict['CON_BEGINS'] = ' '
                proj_dict['CON_ENDS'] = ' '
                proj_dict['RES_ENGR'] = ' '
                proj_dict['MHD_DIST'] = ' '
                proj_dict['CUR_STATUS'] = ' '
                proj_dict['DES_RESP'] = ' '
                proj_dict['ROW_RESP'] = ' '
                proj_dict['ROW_CERT_ISSUED'] = ' '
                proj_dict['EST_CON_COST'] = ' '
                proj_dict['DATE_PRC_APPROVED'] = ' '
                proj_dict['DATE_25_SUBMITTED'] = ' '
                proj_dict['DATE_75_SUBMITTED'] = ' '
                proj_dict['DATE_100_SUBMITTED'] = ' '
                proj_dict['DATE_PSE_SUBMITTED'] = ' '
                proj_dict['BRIDGES'] = ' '
# end_def (of process_project)


# Write the "header" line to the output CSV file for PROJIS projects.
# The header line identifies the database fields extracted into each "column" of the output CSV file.
#
def write_csv_header(csv):
        csv.write("PROJ_NUM" + comma)
        csv.write("PROJ_DESC" + comma)
        csv.write("TOWNS" + comma)
        csv.write("PROJ_TYPE" + comma)
        csv.write("PROJ_STATUS" + comma)
        csv.write("PROJ_TIP_YEAR" + comma)
        csv.write("LONG_DESC" + comma)
        csv.write("CON_BEGINS" + comma)
        csv.write("CON_ENDS" + comma)
        csv.write("RES_ENGR" + comma)
        csv.write("MHD_DIST" + comma)
        csv.write("CUR_STATUS" + comma)
        csv.write("DES_RESP" + comma)
        csv.write("ROW_RESP" + comma)
        csv.write("ROW_CERT_ISSUED" + comma)
        csv.write("EST_CON_COST" + comma)
        csv.write("DATE_PRC_APPROVED" + comma)
        csv.write("DATE_25_SUBMITTED" + comma)
        csv.write("DATE_75_SUBMITTED" + comma)
        csv.write("DATE_100_SUBMITTED" + comma)
        csv.write("DATE_PSE_SUBMITTED" + comma)
        csv.write("BRIDGES")
        csv.write(newline)
# end_def (of write_csv_header)


# Write the data for one PROJIS project to the output CSV file.
# Parameters: pd  - the dictionary for a given PROJIS project.
#             csv - output CSV file
def write_to_csv_file(pd, csv):
        csv.write(pd['PROJ_NUM'] + comma)
        csv.write(pd['PROJ_DESC'] + comma)
        csv.write(pd['TOWNS'] + comma)
        csv.write(pd['PROJ_TYPE'] + comma)
        csv.write(pd['PROJ_STATUS'] + comma)
        csv.write(pd['PROJ_TIP_YEAR'] + comma)
        csv.write(pd['LONG_DESC'] + comma)
        csv.write(pd['CON_BEGINS'] + comma)
        csv.write(pd['CON_ENDS'] + comma)
        csv.write(pd['RES_ENGR'] + comma)
        csv.write(pd['MHD_DIST'] + comma)
        csv.write(pd['CUR_STATUS'] + comma)
        csv.write(pd['DES_RESP'] + comma)
        csv.write(pd['ROW_RESP'] + comma)
        csv.write(pd['ROW_CERT_ISSUED'] + comma)
        csv.write(pd['EST_CON_COST'] + comma)
        csv.write(pd['DATE_PRC_APPROVED'] + comma)
        csv.write(pd['DATE_25_SUBMITTED'] + comma)
        csv.write(pd['DATE_75_SUBMITTED']+ comma)
        csv.write(pd['DATE_100_SUBMITTED'] + comma)
        csv.write(pd['DATE_PSE_SUBMITTED'] + comma)
        csv.write(pd['BRIDGES'])
        csv.write(newline)
# end_def (of write_to_csv_file)
        

# Function process_all_projects().
# This function contains the main loop over all projects in the input HTML file.
def process_all_projects(html_file_name, csv_file_name):
        """
        Function: process_all_projects
        This function iterates over all projects found in html_file_name
        (typically, this the HTML taken from the PROJIS web page for all
        projects in the Boston MPO area, and generates a CSV file named
        csv_file_name containing the attributes extracted for each project.
        This function calls process_one_project to extract the attributes
        for each individual project, found on a "project detail" page.
        """
        global num_exceptions
        # Open HTML file containing list of all project numbers in Boston MPO region.
        html_file = open(html_file_name)
        html_text = html_file.read()

        # Open the output file.
        output_csv = open(csv_file_name, "w")
        write_csv_header(output_csv)

        # Parse the HTML read in above.
        soup = BeautifulSoup(html_text)

        # Find all the <td> nodes of class "prjProjectNumber".
        tds = soup.findAll("td", "prjProjectNumber")

        # Iterate over each node in the list "tds" (one per PROJIS project), and use
        # these nodes and their siblings, and in particular the URL in sibling[1], to
        # extract information about each project.
        count = 0
        for node in tds:
                count = count + 1
                proj = node.parent
                proj_dict = {}
                # project number: formatted as a 6-digit string, padded with leading 0's.
                proj_num = "%06d" % int(proj.contents[1].contents[0].string)
                #
                # Trace output:
                # print str(count) + " " + "Processing project: " + proj_num
                # print "    URL: " + proj.contents[1].contents[0]["href"]
                #
                proj_dict['PROJ_NUM'] = proj_num
                proj_desc = cleanup_string(str(proj.contents[3].string))
                proj_dict['PROJ_DESC'] = proj_desc
                proj_type = str(proj.contents[5].string)
                proj_dict['PROJ_TYPE'] = proj_type
                proj_status = str(proj.contents[7].string)
                proj_dict['PROJ_STATUS'] = proj_status
                proj_tip_year = str(proj.contents[9].string)
                proj_dict['PROJ_TIP_YEAR'] = proj_tip_year
                #
                # Drill down to the page with detailed info on this project,
                # and extract it into proj_dict.
                process_project(proj_num, proj.contents[1].contents[0]["href"], proj_dict)
                #
                # Write a record for the project to the output CSV file.
                write_to_csv_file(proj_dict, output_csv)
                #
        # end_for
        output_csv.close()
        print "Processing of " + str(count) + " projects completed. Number of exceptions = " + str(num_exceptions) + "."
# end_def (of process_all_projects)

# Main routine: generate_dump().
def generate_dump(input_file_name, output_file_name):
        """
        Function: generate_dump(input_file_name, output_file_name).
        This is the main routine of the geenrate_projis_dump module.
        Parameters:
        input_file_name: name of HTML file containing top-level list of PROJIS projects to be processed,
                         typically those in the Boston MPO region.
                         If "" is passed, this defaults to "./boston_mpo.html".
        output_file_name: Name of CSV file into which data extracted from the PROJIS database will be written.
                          If "" is passed, this defaults to "./projis_dump_<month>_<day>_<year>.csv"
        """
        # If input file name is "", use default_html_input_file_name.
        default_html_input_file_name = "./boston_mpo.html"
        if (input_file_name == ""):
                input_file_name = default_html_input_file_name
        # end_if
        # If output_file_name is "", 
        # generate default output file name: "./projis_dump_<month>_<day>_<year>.csv"
        if (output_file_name == ""):
                dt = datetime.date.today()
                default_csv_file_name = "./projis_dump_" + str(dt.month) + "_" + str(dt.day) + "_" + str(dt.year) + ".csv"
                output_file_name = default_csv_file_name
        # end_if
        # Call the main routine, with input and output parms.
        process_all_projects(input_file_name, output_file_name)
# end_def (of generate_dump)
