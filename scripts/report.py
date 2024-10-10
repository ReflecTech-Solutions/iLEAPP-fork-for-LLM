import html
import os
import pathlib
import shutil

from collections import OrderedDict
from scripts.html_parts import *
from scripts.ilapfuncs import logfunc
from scripts.version_info import ileapp_version, ileapp_contributors
from scripts.report_icons import icon_mappings

def get_icon_name(category, artifact):
    """
    Returns the icon name from the feathericons collection. To add an icon type for
    an artifact, select one of the types from ones listed @ feathericons.com
    If no icon is available, the alert triangle is returned as default icon.
    """
    category = category.upper()
    artifact = artifact.upper()

    category_match = icon_mappings.get(category)

    if category_match:
        if isinstance(category_match, str):
            return category_match
        elif isinstance(category_match, dict):
            artifact_match = category_match.get(artifact)
            if artifact_match:
                return artifact_match
            else:
                if category_match.get('_mode') == 'search':
                    for key, value in category_match.items():
                        if artifact.find(key) >= 0:
                            return value
                    art_default = category_match.get('default')
                    if art_default:
                        return art_default
                art_default = category_match.get('default')
                if art_default:
                    return art_default
    else:
        # search_set = get_search_mode_categories()
        for r in search_set:
            for record in search_set:
                category_key, category_mapping = list(record.items())[0]
                if category.find(category_key) >= 0:
                    for key, value in category_mapping.items():
                        if artifact.find(key) >= 0:
                            return value
                    art_default = category_mapping.get('default')
                    if art_default:
                        return art_default

    return 'alert-triangle'


def get_search_mode_categories():
    search_mode_categories = []
    for category, mappings in icon_mappings.items():
        if isinstance(mappings, dict) and mappings.get('_mode') == 'search':
            search_mode_categories.append({category: mappings})
    return search_mode_categories
# get them populated
search_set = get_search_mode_categories()


def generate_report(reportfolderbase, time_in_secs, time_HMS, extraction_type, image_input_path, casedata, profile_filename):
    control = None
    side_heading = \
        """
        <h6 class="sidebar-heading justify-content-between align-items-center px-3 mt-4 mb-1 text-muted">
            {0}
        </h6>
        """
    list_item = \
        """
        <li class="nav-item">
            <a class="nav-link {0}" href="{1}">
                <span data-feather="{2}"></span> {3}
            </a>
        </li>
        """
    # Populate the sidebar dynamic data (depends on data/files generated by parsers)
    # Start with the 'saved reports' (home) page link and then append elements
    nav_list_data = side_heading.format('Saved Reports') + list_item.format('', 'index.html', 'home', 'Report Home')
    # Get all files
    side_list = OrderedDict() # { Category1 : [path1, path2, ..], Cat2:[..] } Dictionary containing paths as values, key=category

    for root, dirs, files in sorted(os.walk(reportfolderbase)):
        files = sorted(files)
        for file in files:
            if file.endswith(".temphtml"):
                fullpath = (os.path.join(root, file))
                head, tail = os.path.split(fullpath)
                p = pathlib.Path(fullpath)
                SectionHeader = (p.parts[-2])
                if SectionHeader == '_elements':
                    pass
                else:
                    if control != SectionHeader:
                        control = SectionHeader
                        side_list[SectionHeader] = []
                        nav_list_data += side_heading.format(SectionHeader)
                    side_list[SectionHeader].append(fullpath)
                    icon = get_icon_name(SectionHeader, tail.replace(".temphtml", ""))
                    nav_list_data += list_item.format('', tail.replace(".temphtml", ".html"), icon,
                                                        tail.replace(".temphtml", "").replace("_", " "))

    # Now that we have all the file paths, start writing the files

    for category, path_list in side_list.items():
        for path in path_list:
            old_filename = os.path.basename(path)
            filename = old_filename.replace(".temphtml", ".html")
            # search for it in nav_list_data, then mark that one as 'active' tab
            active_nav_list_data = mark_item_active(nav_list_data, filename) + nav_bar_script
            artifact_data = get_file_content(path)

            # Now write out entire html page for artifact
            f = open(os.path.join(reportfolderbase, '_HTML', filename), 'w', encoding='utf8')
            artifact_data = insert_sidebar_code(artifact_data, active_nav_list_data, path)
            f.write(artifact_data)
            f.close()

            # Now delete .temphtml
            os.remove(path)
            # If dir is empty, delete it
            try:
                os.rmdir(os.path.dirname(path))
            except OSError:
                pass # Perhaps it was not empty!

    # Create index.html's page content
    create_index_html(reportfolderbase, time_in_secs, time_HMS, extraction_type, image_input_path, nav_list_data, casedata, profile_filename)
    elements_folder = os.path.join(reportfolderbase, '_HTML', '_elements')
    __location__ = os.path.dirname(os.path.abspath(__file__))

    def copy_no_perm(src, dst, *, follow_symlinks=True):
        if not os.path.isdir(dst):
            shutil.copyfile(src, dst)
        return dst

    try:
        shutil.copytree(os.path.join(__location__, "_elements"), elements_folder, copy_function=copy_no_perm)
    except shutil.Error:
        print("shutil reported an error. Maybe due to recursive directory copying.")
        if os.path.exists(os.path.join(elements_folder, 'MDB-Free_4.13.0')):
            print("_elements folder seems fine. Probably nothing to worry about")


def get_file_content(path):
    f = open(path, 'r', encoding='utf8')
    data = f.read()
    f.close()
    return data

def create_index_html(reportfolderbase, time_in_secs, time_HMS, extraction_type, image_input_path, nav_list_data, casedata, profile_filename):
    '''Write out the index.html page to the report folder'''
    case_list = []
    content = '<br />'
    content += """
                   <div class="card bg-white" style="padding: 20px;">
                   <h2 class="card-title">Case Information</h2>
               """  # CARD start

    if len(casedata) > 0:
        for key, value in casedata.items():
            if value:
                case_list.append([key, value])
    
    if profile_filename:
        case_list.append(['Profile loaded', profile_filename])
    
    case_list += [
        ['Extraction location', image_input_path],
        ['Extraction type', extraction_type],
        ['Report directory', reportfolderbase],
        ['Processing time', f'{time_HMS} (Total {time_in_secs} seconds)']
    ]
    
    tab1_content = generate_key_val_table_without_headings('', case_list) + \
        """
            <p class="note note-primary mb-4">
            All dates and times are in UTC unless noted otherwise!
            </p>
        """

    # Get script run log (this will be tab2)
    devinfo_files_path = os.path.join(reportfolderbase, 'Script Logs', 'DeviceInfo.html')
    tab2_content = get_file_content(devinfo_files_path)

    # Get script run log (this will be tab3)
    script_log_path = os.path.join(reportfolderbase, 'Script Logs', 'Screen Output.html')
    tab3_content = get_file_content(script_log_path)

    # Get processed files list (this will be tab3)
    processed_files_path = os.path.join(reportfolderbase, 'Script Logs', 'ProcessedFilesLog.html')
    tab4_content = get_file_content(processed_files_path)

    content += tabs_code.format(tab1_content, tab2_content, tab3_content, tab4_content)

    content += '</div>'  # CARD end

    authors_data = generate_authors_table_code(ileapp_contributors)
    credits_code = credits_block.format(authors_data)

    # WRITE INDEX.HTML LAST
    filename = 'index.html'
    page_title = 'iLEAPP Report'
    body_heading = 'iOS Logs, Events, And Plists Parser'
    body_description = 'iLEAPP is an open source project that aims to parse every known iOS artifact for the purpose of forensic analysis.'
    active_nav_list_data = mark_item_active(nav_list_data, filename) + nav_bar_script

    f = open(os.path.join(reportfolderbase, '_HTML', filename), 'w', encoding='utf8')
    f.write(page_header.format(page_title))
    f.write(body_start.format(f"iLEAPP {ileapp_version}"))
    f.write(body_sidebar_setup + active_nav_list_data + body_sidebar_trailer)
    f.write(body_main_header + body_main_data_title.format(body_heading, body_description))
    f.write(content)
    f.write(thank_you_note)
    f.write(credits_code)
    f.write(body_main_trailer + body_end + nav_bar_script_footer + page_footer)
    f.close()

    # Create Index Redirection Page
    redirection = \
        """
        <html>
            <head>
                <meta http-equiv="refresh" content="0; url=_HTML/index.html" />
                <title>iLEAPP Report</title>
            </head>
        </html>
        """
    f = open(os.path.join(reportfolderbase, filename), 'w', encoding='utf8')
    f.write(redirection)
    f.close()



def generate_authors_table_code(ileapp_contributors):
    authors_data = ''
    for author_name, blog, tweet_handle, git in ileapp_contributors:
        author_data = ''
        if blog:
            author_data += f'<a href="{blog}" target="_blank">{blog_icon}</a> &nbsp;\n'
        else:
            author_data += f'{blank_icon} &nbsp;\n'
        if tweet_handle:
            author_data += f'<a href="https://twitter.com/{tweet_handle}" target="_blank">{twitter_icon}</a> &nbsp;\n'
        else:
            author_data += f'{blank_icon} &nbsp;\n'
        if git:
            author_data += f'<a href="{git}" target="_blank">{github_icon}</a>\n'
        else:
            author_data += f'{blank_icon}'

        authors_data += individual_contributor.format(author_name, author_data)
    return authors_data

def generate_key_val_table_without_headings(title, data_list, html_escape=True, width="70%"):
    '''Returns the html code for a key-value table (2 cols) without col names'''
    code = ''
    if title:
        code += f'<h2>{title}</h2>'
    table_header_code = \
        """
        <div class="table-responsive">
            <table class="table table-bordered table-hover table-sm" width={}>
                <tbody>
        """
    table_footer_code = \
        """
                </tbody>
            </table>
        </div>
        """
    code += table_header_code.format(width)

    # Add the rows
    if html_escape:
        for row in data_list:
            code += '<tr>' + ''.join( ('<td>{}</td>'.format(html.escape(str(x))) for x in row) ) + '</tr>'
    else:
        for row in data_list:
            code += '<tr>' + ''.join( ('<td>{}</td>'.format(str(x)) for x in row) ) + '</tr>'

    # Add footer
    code += table_footer_code

    return code

def insert_sidebar_code(data, sidebar_code, filename):
    pos = data.find(body_sidebar_dynamic_data_placeholder)
    if pos < 0:
        logfunc(f'Error, could not find {body_sidebar_dynamic_data_placeholder} in file {filename}')
        return data
    else:
        ret = data[0: pos] + sidebar_code + data[pos + len(body_sidebar_dynamic_data_placeholder):]
        return ret

def mark_item_active(data, itemname):
    '''Finds itemname in data, then marks that node as active. Return value is changed data'''
    pos = data.find(f'" href="{itemname}"')
    if pos < 0:
        logfunc(f'Error, could not find {itemname} in {data}')
        return data
    else:
        ret = data[0: pos] + " active" + data[pos:]
        return ret
    
    
    
