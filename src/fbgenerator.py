import argparse
import math
import os
import sys
import xml.etree.ElementTree as ET
import argparse
from re import sub

def parse_arguments():
    """
    Parse command line arguments.

    Returns:
        argparse.Namespace: Parsed command line arguments.
    """
    parser = argparse.ArgumentParser(description="Parse XML and extract values of <include> nodes.")
    parser.add_argument('--input', required=True, help='Path to the XML files')
    parser.add_argument('--output', required=True, help='Path to the generated FlatBuffers files')
    return parser.parse_args()


# Define a function to convert a string to camel case
def camel_case(s):
    # Use regular expression substitution to replace underscores and hyphens with spaces,
    # then title case the string (capitalize the first letter of each word), and remove spaces
    s = sub(r"(_|-)+", " ", s).title().replace(" ", "")

    # Join the string, ensuring the first letter is lowercase
    return ''.join([s[0].lower(), s[1:]])



def process_command(entry_name_arg, param_list_arg, fbsfile_arg):
    print(f"\t\t- Generating the command {entry_name_arg}")
    
    # Writes the beginning of the table
    fbsfile_arg.write(f"\n\n// Command {entry_name_arg}\n")
    fbsfile_arg.write(f"table {entry_name_arg} {{\n")
    
    # Creates the table field declarations
    for param in param_list_arg:
        param_index = param.get('index')
        param_label = param.get('label')
        param_min_value = param.get('minValue')
        param_max_value = param.get('maxValue')
        param_increment = param.get('increment')
        param_units = param.get('units')
        param_description = param.text

        if (param_description != None):
            fbsfile_arg.write("\t// " + param_description.replace('\n', '\n\t//') + "\n")
            
        if ( param_min_value != None):
            fbsfile_arg.write(f"\t// minValue: {param_min_value};\n")    

        if ( param_max_value != None):
            fbsfile_arg.write(f"\t// maxValue: {param_max_value};\n")
            
        if ( param_increment != None): 
            fbsfile_arg.write(f"\t// increment: {param_increment};\n")
            
        if ( param_units != None):
            fbsfile_arg.write(f"\t// units: {param_units};\n")
                
        if ( param_label == None):
            param_label = f"param{param_index}"

        fbsfile_arg.write(f"\t{camel_case(param_label)}:float;\n")

    # Writes the end of the table           
    fbsfile_arg.write("}\n\n")       
    
    

def process_enum(filename_arg, fbsfile_arg, enum_element_arg, default_enum_values_map_arg):
    entry_list = enum_element_arg.findall('entry')

    if (default_enum_values_map_arg.get(filename_arg) == None):
        default_enum_values_map_arg[filename_arg] = {}

    if (entry_list != None and len(entry_list) > 0):
        description = enum_element_arg.find('description')
        enum_definition_list = []
        command_definition_list = []
        enum_name = enum_element_arg.get('name')

        if (description != None):
           cleaned_description = description.text.replace('\n', '\n//')
           fbsfile_arg.write(f"// {cleaned_description}\n")

        for entry in entry_list:
            entry_name= entry.get('name')
            param_list = entry.findall('param')
        
            if (param_list != None and len(param_list) > 0):
               process_command(entry_name, param_list, fbsfile_arg)
            else:    
               print(f"\t\t- Generating the enum entry {enum_name}/{entry_name}")

    fbsfile_arg.write("\n")


def prepare_files(include_map_arg, default_enum_values_map_arg,input_dir_arg, output_dir_arg):
    # Iterate through XML files in the specified folder
    for filename in os.listdir(input_dir_arg):
        if filename.endswith(".xml"):
            include_list = []
            # Parse the XML data from the file
            tree = ET.parse(os.path.join(input_dir_arg, filename))
            root = tree.getroot()
            filename = f"{filename.replace('.xml', '')}"
            flatbuffer_filename = os.path.join(
                output_dir_arg, f"{filename}.fbs")

            print(f"\t- Preparing the flatbutffer file for {filename}")

            # Write the values to a file
            with open(flatbuffer_filename, 'w') as fbsfile:
               include_values = [
                   include.text for include in root.findall('.//include')]

               for value in include_values:
                   include_filename = value.replace('.xml', '')

                   include_list.append(include_filename)

                   fbsfile.write(f'include "{include_filename}.fbs";\n')

               fbsfile.write("\n\nnamespace uav4pi;\n\n")

               # Extract information from enums
               for enum_element in root.findall('.//enum'):
                   process_enum(filename, fbsfile, enum_element, default_enum_values_map_arg)

               include_map_arg[filename] = include_list


def main():
    # Parse command-line arguments
    args = parse_arguments()
    flattened_include_map = {}
    default_enum_values_map_arg = {}

    print("Starting the XML conversion")
    prepare_files(flattened_include_map, default_enum_values_map_arg, args.input, args.output)


if __name__ == "__main__":
    main()

