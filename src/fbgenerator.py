import argparse
import math
import os
import sys
import xml.etree.ElementTree as ET

default_enum_values = {}


import argparse

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


def guess_type_from_min_max(min_enum_value_arg, max_enum_value_arg):
    if (min_enum_value_arg <= 127):
        if (min_enum_value_arg >= 0):
           result = 'ubyte'
        else:
           result = 'byte'
    elif (max_enum_value_arg <= 32767):
        if (min_enum_value_arg >= 0):
            result = 'ushort'
        else:
            result = 'short'
    elif (min_enum_value_arg >= 0):
        result = 'uint64'
    else:
        result = 'int64'

    return result


def extract_enum_info(filename_arg, fbsfile_arg,enum_element_arg):
    line_count = 0;
    description = enum_element_arg.find('description')
    min_enum_value = math.nan 
    max_enum_value = math.nan 
    min_enum_id = ''
    enum_name = enum_element_arg.get('name')
    enum_definition = ''
    
    if ( default_enum_values.get(filename_arg) == None ):
        default_enum_values[filename_arg] = {}    

    if ( description != None):
        cleaned_description = description.text.replace('\n', '\n//');

        fbsfile_arg.write(f"// {cleaned_description}\n")

    for field_element in enum_element_arg.findall('entry'):
        value = int(field_element.get('value', ''));

        if ( line_count > 0):
            enum_definition = enum_definition + ",\n"

        enum_definition = enum_definition + (f"   {field_element.get('name')}={field_element.get('value', '')}")

        if ( math.isnan(min_enum_value) or  (value < min_enum_value)):
            min_enum_value = value
            min_enum_id = field_element.get('name')        

        if ( math.isnan(max_enum_value) ):
            max_enum_value = value

        max_enum_value = max(max_enum_value, value)

        line_count = line_count + 1

    enum_type = guess_type_from_min_max(min_enum_value, max_enum_value)
    fbsfile_arg.write(f"enum {enum_name} : {enum_type}")
    fbsfile_arg.write("\n{\n")
    fbsfile_arg.write(enum_definition)
    fbsfile_arg.write("\n}\n\n")

    default_enum_values[filename_arg][enum_name] = min_enum_id

    fbsfile_arg.write("\n")


def extract_message_info(file_arg, message_element_arg, default_enum_values_map_arg):
    description = message_element_arg.find('description')

    if ( description != None ):
        cleaned_description = description.text.replace('\n', '\n//');

        file_arg.write(f"// {cleaned_description}\n")

    file_arg.write(f"table {message_element_arg.get('name')}")
    file_arg.write(" {\n")
    file_arg.write(f"   _id:uint = {message_element_arg.get('id')};\n")
    file_arg.write("\n")

    for field_element in message_element_arg.findall('field'):
        file_arg.write(f"   // {field_element.text}\n")

        if (not field_element.get('enum', '').strip()):
            field_type = field_element.get('type').replace('uint8_t', 'ubyte') \
                                                  .replace('int8_t', 'byte') \
                                                  .replace('uint16_t', 'ushort') \
                                                  .replace('int16_t', 'short') \
                                                  .replace('uint32_t', 'uint') \
                                                  .replace('int32_t', 'int') \
                                                  .replace('float32_t', 'float') \
                                                  .replace('uint64_t', 'uint64') \
                                                  .replace('int64_t', 'int64') \
                                                  .replace('float64_t', 'float64')

            # Test if it is an array
            if ( "[" in field_type ):
                field_type = "[" + field_type.replace('[','')

            file_arg.write(f"   {field_element.get('name')}:{field_type};\n")
        else:
            enum_name = field_element.get('enum', '')

            file_arg.write(
                f"   {field_element.get('name')}:{enum_name} = {default_enum_values_map_arg[enum_name]};\n")

    file_arg.write("}\n\n")

def xml_to_flatbuffers(root_node_arg, flatbuffer_file_arg, all_default_values_arg):
    # Extract information from messages
    for message_element in root_node_arg.findall('.//messages/message'):
        extract_message_info(flatbuffer_file_arg,
                             message_element, all_default_values_arg)


def prepare_files(include_map_arg, input_dir_arg, output_dir_arg):
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
                   extract_enum_info(filename, fbsfile, enum_element)
               
               include_map_arg[filename] = include_list


def convert_xml_files(include_map_arg, input_dir_arg, output_dir_arg):
    for filename in os.listdir(input_dir_arg):
        if filename.endswith(".xml"):
            # Parse the XML data from the file
            tree = ET.parse(os.path.join(input_dir_arg, filename))
            root = tree.getroot()
            filename = filename.replace('.xml', '')
            include_map = include_map_arg[filename]
            all_default_values = {}
            flatbuffer_filename = os.path.join(
                output_dir_arg, f'{filename}.fbs')

            if ( default_enum_values.get(filename) != None ):
               all_default_values = default_enum_values[filename]
               
            for include in include_map:
                if (default_enum_values.get(include) != None):
                   all_default_values = {**all_default_values, **default_enum_values[include]}
            
            print(f"\t- Converting {filename}.xml")
            with open(flatbuffer_filename, 'a') as file:
                xml_to_flatbuffers(root, file, all_default_values)


def main():
    # Parse command-line arguments
    args = parse_arguments()
    include_map = {}

    print("Starting the XML conversion")

    prepare_files(include_map, args.input, args.output)
    convert_xml_files(include_map, args.input, args.output)


if __name__ == "__main__":
    main()

