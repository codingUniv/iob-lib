#!/usr/bin/env python3
#
#    Build Latex tables of verilog module interface signals and registers
#

import sys
from parse import parse
import math
from verilog2tex import header_parse

#name, type, address, width, default value, description

def has_mem_type(table):
    for reg in table:
        if reg["reg_type"] == "MEM":
            return 1
    return 0

def gen_mem_wires(table, fout):
    fout.write(f"\n//mem wires\n")
    for reg in table:
        if reg["reg_type"] == "MEM":
            name = reg["name"]
            addr_w = reg["addr_w"]
            width = reg["width"]
            fout.write(f"`IOB_VAR({name}_addr_int, {addr_w})\n")
            if reg["rw_type"] == "W":
                fout.write(f"`IOB_VAR({name}_wdata_int, {width})\n")
                fout.write(f"`IOB_VAR({name}_wstrb_int, {width}/8)\n")
            else:
                fout.write(f"`IOB_VAR({name}_rdata_int, {width})\n")
                fout.write(f"`IOB_VAR({name}_ren_int, 1)\n")
    fout.write(f"\n")

# Obtain Address range between memories (if addresses are already calculated)
def get_mem_range(table):
    for reg in table:
        if reg["reg_type"] == "MEM":
            return reg["addr"]
    return 0

def gen_mem_writes(table, fout):
    fout.write(f"\n//mem write logic\n")
    for reg in table:
        if reg["reg_type"] == "MEM":
            if reg["rw_type"] == "W":
                name = reg["name"]
                addr_w = reg["addr_w"]
                width = reg["width"]
                addr = str(int(reg["addr"])>>2)
                mem_range_w = str(int(math.log(int(get_mem_range(table))>>2, 2)))
                fout.write(f"`IOB_COMB {name}_addr_int = address[{addr_w}-1:0];\n")
                fout.write(f"`IOB_COMB {name}_wdata_int = wdata[{width}-1:0];\n")
                fout.write(f"`IOB_COMB {name}_wstrb_int = (valid & ( (address[ADDR_W-1:{mem_range_w}] << {mem_range_w}) == {addr})) ? wstrb : {{(DATA_W/8){{1'b0}}}};\n")

def gen_mem_reads(table, fout):
    has_mem_reads = 0
    fout.write(f"\n//mem read logic\n")
    for reg in table:
        if reg["reg_type"] == "MEM":
            if reg["rw_type"] == "R":
                has_mem_reads = 1
                name = reg["name"]
                addr_w = reg["addr_w"]
                addr = str(int(reg["addr"])>>2)
                mem_range_w = str(int(math.log(int(get_mem_range(table))>>2, 2)))
                fout.write(f"`IOB_COMB {name}_addr_int = address[{addr_w}-1:0];\n")
                fout.write(f"`IOB_COMB {name}_ren_int = (valid & ( (address[ADDR_W-1:{mem_range_w}] << {mem_range_w}) == {addr}));\n")

    # switch case for mem reads
    if has_mem_reads:
        fout.write(f"`IOB_VAR(mem_address, ADDR_W)\n")
        mem_range_w = str(int(math.log(int(get_mem_range(table))>>2, 2)))
        fout.write(f"`IOB_COMB mem_address = address[ADDR_W-1:{mem_range_w}] << {mem_range_w};\n")
        fout.write(f"always @* begin\n")
        fout.write(f"\tcase(mem_address)\n")
        for reg in table:
            if reg["reg_type"] == "MEM":
                if reg["rw_type"] == "R":
                    addr = str(int(reg["addr"])>>2)
                    fout.write(f"\t\t{addr}: mem_rdata_int = {name}_rdata_int;\n")
        fout.write(f"\t\tdefault: mem_rdata_int = 1'b0;\n")
        fout.write(f"\tendcase\n")
        fout.write(f"end\n")


def write_hw(table, regvfile_name):

    fout = open (regvfile_name+'_gen.vh', 'w')

    fout.write("//This file was generated by script mkregs.py\n\n")

    fout.write("\n\n//write registers\n")
    for row in table:
        if row["reg_type"] == "REG":
            name = row["name"]
            typ = row["rw_type"]
            address = row["addr"]
            width = row["width"]
            default_val = row["default_value"]

            if (typ == 'W'):
                fout.write("`IOB_REG_ARE(clk, rst, " + default_val + ", valid & wstrb & (address == " + str(int(address)>>2) + "), "
                           + name + ", wdata["+width+"-1:0])\n")
            else:
                continue

    fout.write("\n\n//read registers\n")
    fout.write("`IOB_VAR(mem_rdata_int, DATA_W)\n")
    fout.write("`IOB_VAR(rdata_int, DATA_W)\n")
    fout.write("`IOB_VAR(rdata_int2, DATA_W)\n")
    fout.write("`IOB_REG_ARE(clk, rst, 0, valid, rdata_int2, rdata_int)\n")
    fout.write("`IOB_VAR2WIRE(rdata_int2, rdata)\n\n")

    fout.write("always @* begin\n")
    fout.write("   case(address)\n")

    for row in table:
        if row["reg_type"] == "REG":
            name = row["name"]
            typ = row["rw_type"]
            address = row["addr"]
            width = row["width"]
            default_val = row["default_value"]

            if (typ == 'R'):
                fout.write("     " + str(int(address)>>2) + ": rdata_int = " + name + ";\n")
            else:
                continue

    fout.write("     default: rdata_int = mem_rdata_int;\n")
    fout.write("   endcase\n")
    fout.write("end\n")

    #ready signal
    fout.write("`IOB_VAR(ready_int, 1)\n")
    fout.write("`IOB_REG_AR(clk, rst, 0, ready_int, valid)\n")
    fout.write("`IOB_VAR2WIRE(ready_int, ready)\n")

    #Memory section
    if has_mem_type(table):
        gen_mem_wires(table, fout)
        gen_mem_writes(table, fout)
        gen_mem_reads(table, fout)
    else:
        fout.write("`IOB_COMB mem_rdata_int = 1'b0;\n")

    fout.close()

def get_core_addr_w(table):
    max_addr = 0
    max_addr_from_mem = 0
    for reg in table:
        if int(reg["addr"]) > max_addr:
            max_addr = int(reg["addr"])
            if reg["reg_type"] == "MEM":
                max_addr_from_mem = 1
            else:
                max_addr_from_mem = 0

    if max_addr_from_mem:
        max_addr = max_addr + int(get_mem_range(table)) 

    hw_max_addr = max_addr >> 2
    addr_w = int(math.ceil(math.log(hw_max_addr, 2)))
    return addr_w

def write_hwheader(table, regvfile_name):

    fout = open(regvfile_name+'_def.vh', 'w')

    fout.write("//This file was generated by script mkregs.py\n\n")

    fout.write("//address width\n")
    fout.write("`define " + regvfile_name + "_ADDR_W " + str(get_core_addr_w(table)) + "\n\n")

    fout.write("//address macros\n")
    fout.write("//SWREGs\n")
    for row in table:
        if row["reg_type"] == "REG":
            name = row["name"]
            address = row["addr"]
            fout.write("`define " + name + "_ADDR " + str(int(address)>>2) + "\n")
    fout.write("//SWMEMs\n")
    for row in table:
        if row["reg_type"] == "MEM":
            name = row["name"]
            address = row["addr"]
            fout.write("`define " + name + "_ADDR " + str(int(address)>>2) + "\n")

    fout.write("\n//registers/mems width\n")
    for row in table:
        name = row["name"]
        width = row["width"]
        fout.write("`define " + name + "_W " + width + "\n")

    fout.write("\n//mem address width\n")
    for row in table:
        if row["reg_type"] == "MEM":
            name = row["name"]
            mem_addr_w = row["addr_w"]
            fout.write("`define " + name + "_ADDR_W " + mem_addr_w + "\n")

    fout.close()

# Read vh files to get non-literal widths
def get_defines():
    # .vh file lines
    vh = []

    if(len(sys.argv) > 4):
        i = 4
        while i<len(sys.argv) and sys.argv[i].find('.vh'):
            fvh =  open (sys.argv[i], 'r')
            vh = [*vh, *fvh.readlines()]
            fvh.close()
            i = i+1

    defines = {}
    #parse headers if any
    if vh: 
        header_parse(vh, defines)

    return defines


# Get C type from swreg width
# uses unsigned int types from C stdint library
# width: SWREG width
def swreg_type(width, defines):
    # Check if width is a number string (1, 8, 15, etc)
    try:
        width_int = int(width)
    except:
        # width is a parameter or macro (example: DATA_W, ADDR_W)
        eval_str = width.replace('`','').replace(',','')
        for key, val in defines.items():
            eval_str = eval_str.replace(str(key),str(val))
        try:
            width_int = int(eval_str)
        except:
            #eval_str has undefined parameters: use default value
            width_int = 32

    if width_int < 1:
        print(f'MKREGS: invalid SWREG width value {width}.')
        width_int = 32
    
    type_dict = {
        8: 'uint8_t',
        16: 'uint16_t',
        32: 'uint32_t',
        64: 'uint64_t'
    }
    default_width = 'uint64_t'
    
    # next 8*2^k last enough to store width
    next_pow2 = 2**(math.ceil(math.log2(math.ceil(width_int/8))))
    sw_width = 8*next_pow2

    return type_dict.get(sw_width, default_width)

def write_swheader(table, regvfile_name, core_prefix, defines):

    fout = open(regvfile_name+'.h', 'w')

    fout.write("//This file was generated by script mkregs.py\n\n")
    fout.write(f"#ifndef H_IOB_{core_prefix}_SWREG_H\n")
    fout.write(f"#define H_IOB_{core_prefix}_SWREG_H\n\n")
    fout.write("#include <stdint.h>\n\n")

    fout.write("//register address mapping\n")
    for row in table:
        if row["reg_type"] == "REG":
            name = row["name"]
            address = row["addr"]
            fout.write("#define " + name + " " + address + "\n")
    fout.write("//memory address mapping\n")
    for row in table:
        if row["reg_type"] == "MEM":
            name = row["name"]
            address = row["addr"]
            fout.write("#define " + name + " " + address + "\n")

    fout.write("\n// Base Address\n")
    fout.write("static int base;\n")
    fout.write(f"void {core_prefix}_INIT_BASEADDR(uint32_t addr);\n")

    fout.write("\n// Core Setters\n")
    for row in table:
        read_write = row["rw_type"]
        if read_write == "W":
            name = row["name"]
            width = row["width"]
            parsed_name = name.split("_",1)[1]
            sw_type = swreg_type(width, defines)
            if row["reg_type"] == "REG":
                fout.write(f"void {core_prefix}_SET_{parsed_name}({sw_type} value);\n")
            elif row["reg_type"] == "MEM":
                addr_w = row["addr_w"]
                addr_type = swreg_type(addr_w, defines)
                fout.write(f"void {core_prefix}_SET_{parsed_name}({addr_type} addr, {sw_type} value);\n")

    fout.write("\n// Core Getters\n")
    for row in table:
        read_write = row["rw_type"]
        if read_write == "R":
            name = row["name"]
            width = row["width"]
            parsed_name = name.split("_",1)[1]
            sw_type = swreg_type(width, defines)
            if row["reg_type"] == "REG":
                fout.write(f"{sw_type} {core_prefix}_GET_{parsed_name}();\n")
            elif row["reg_type"] == "MEM":
                addr_w = row["addr_w"]
                addr_type = swreg_type(addr_w, defines)
                fout.write(f"{sw_type} {core_prefix}_GET_{parsed_name}({addr_type} addr);\n")


    fout.write(f"\n#endif // H_IOB_{core_prefix}_SWREG_H\n")

    fout.close()

def write_sw_emb(table, regvfile_name, core_prefix, defines):

    fout = open(regvfile_name+'_emb.c', 'w')

    fout.write("//This file was generated by script mkregs.py\n\n")

    swheader_name = regvfile_name+'.h'
    fout.write(f"#include \"{swheader_name}\"\n\n")

    fout.write("\n// Base Address\n")
    fout.write(f"void {core_prefix}_INIT_BASEADDR(uint32_t addr) {{\n")
    fout.write(f"\tbase = addr;\n")
    fout.write(f"}}\n")

    fout.write("\n// Core Setters\n")
    for row in table:
        read_write = row["rw_type"]
        if read_write == "W":
            name = row["name"]
            width = row["width"]
            parsed_name = name.split("_",1)[1]
            sw_type = swreg_type(width, defines)
            if row["reg_type"] == "REG":
                fout.write(f"void {core_prefix}_SET_{parsed_name}({sw_type} value) {{\n")
                fout.write(f"\t(*( (volatile {sw_type} *) ( (base) + ({name}) ) ) = (value));\n")
                fout.write(f"}}\n\n")
            elif row["reg_type"] == "MEM":
                addr_w = row["addr_w"]
                addr_type = swreg_type(addr_w, defines)
                fout.write(f"void {core_prefix}_SET_{parsed_name}({addr_type} addr, {sw_type} value) {{\n")
                fout.write(f"\t(*( (volatile {sw_type} *) ( (base) + ({name}) + (addr<<2) ) ) = (value));\n")
                fout.write(f"}}\n\n")

    fout.write("\n// Core Getters\n")
    for row in table:
        read_write = row["rw_type"]
        if read_write == "R":
            name = row["name"]
            width = row["width"]
            parsed_name = name.split("_",1)[1]
            sw_type = swreg_type(width, defines)
            if row["reg_type"] == "REG":
                fout.write(f"{sw_type} {core_prefix}_GET_{parsed_name}() {{\n")
                fout.write(f"\treturn (*( (volatile {sw_type} *) ( (base) + ({name}) ) ));\n")
                fout.write(f"}}\n\n")
            elif row["reg_type"] == "MEM":
                addr_w = row["addr_w"]
                addr_type = swreg_type(addr_w, defines)
                fout.write(f"{sw_type} {core_prefix}_GET_{parsed_name}({addr_type} addr) {{\n")
                fout.write(f"\treturn (*( (volatile {sw_type} *) ( (base) + ({name}) + (addr<<2) ) ));\n")
                fout.write(f"}}\n\n")

    fout.close()

# Obtain REG only fields
def swreg_parse_reg(swreg_flds, parsed_line):
    #DEFAULT VALUE
    swreg_flds["default_value"] = parsed_line[4]
    return swreg_flds

# Obtain MEM only fields
def swreg_parse_mem(swreg_flds, parsed_line):
    # ADDR_W
    swreg_flds["addr_w"] = parsed_line[4]
    return swreg_flds

# Calculate REG and MEM addresses
def calc_swreg_addr(table):
    reg_addr = 0

    # REGs have initial addresses
    for reg in table:
        if reg["reg_type"] == "REG":
            reg["addr"] = str(reg_addr)
            reg_addr = reg_addr + 4

    mem_range = reg_addr
    # Obtain largest MEM range (or reg range)
    for reg in table:
        if reg["reg_type"] == "MEM":
            # Note x4 factor to use software addresses
            mem_range_tmp = 2**(int(reg["addr_w"]))*4
            if mem_range_tmp > mem_range:
                mem_range = mem_range_tmp

    reg_addr = mem_range
    # Assign MEM addresses
    for reg in table:
        if reg["reg_type"] == "MEM":
            reg["addr"] = str(reg_addr)
            reg_addr = reg_addr + mem_range

    return table

def swreg_parse (code, hwsw, regvfile_name, core_prefix):
    swreg_addr = 0
    table = [] #name, regtype, rwtype, address, width, default value, description

    for line in code:

        swreg_flds = {}
        swreg_flds_tmp = parse('{}`IOB_SW{}_{}({},{},{}){}//{}', line)

        if swreg_flds_tmp is None:
            swreg_flds_tmp = parse('`IOB_SW{}_{}({},{},{}){}//{}', line)
            if swreg_flds_tmp is None: continue #not a sw reg
        else:
            swreg_flds_tmp = swreg_flds_tmp[1:]

        # Common fields for REG and MEM
        #REG_TYPE
        swreg_flds["reg_type"] = swreg_flds_tmp[0]

        #RW_TYPE
        swreg_flds["rw_type"] = swreg_flds_tmp[1]
        
        #NAME
        swreg_flds["name"] = swreg_flds_tmp[2].strip(' ')
        
        #WIDTH
        swreg_flds["width"] = swreg_flds_tmp[3]

        #DESCRIPTION
        swreg_flds["description"] = swreg_flds_tmp[6]

        # REG_TYPE specific fields
        if swreg_flds["reg_type"] == "REG":
            swreg_flds = swreg_parse_reg(swreg_flds, swreg_flds_tmp)
        elif swreg_flds["reg_type"] == "MEM":
            swreg_flds = swreg_parse_mem(swreg_flds, swreg_flds_tmp)

        table.append(swreg_flds)

    # Calculate Address field
    table = calc_swreg_addr(table)


    if(hwsw == "HW"):
        write_hwheader(table, regvfile_name)
        write_hw(table, regvfile_name)

    elif(hwsw == "SW"):
        defines = get_defines()
        write_swheader(table, regvfile_name, core_prefix, defines)
        write_sw_emb(table, regvfile_name, core_prefix, defines)

def print_usage():
    print("Usage: ./mkregs.py TOP_swreg.vh [HW|SW] [CORE_PREFIX] [vh_files]")
    print(" TOP_swreg.vh:the software accessible registers definitions file")
    print(" [HW|SW]: use HW to generate the hardware files or SW to generate the software files")
    print(" [CORE_PREFIX]: (SW only) core prefix name. This is added as sw function prefix")
    print(" [vh_files]: (SW only) paths to .vh files used to extract macro values")

def main () :

    #parse command line
    if len(sys.argv) < 3:
        print_usage()
        quit()
    else:
        regvfile_name = sys.argv[1]
        hwsw = sys.argv[2]

    core_prefix = ""
    if hwsw == "SW":
        try:
            core_prefix = sys.argv[3]
        except:
            print("Expected [CORE_PREFIX] in SW mode. Check Usage.")
            print_usage()
            quit()


    #parse input file
    fin = open (regvfile_name, 'r')
    defsfile = fin.readlines()
    fin.close()

    regvfile_name = regvfile_name.split('/')[-1].split('.')[0]

    swreg_parse (defsfile, hwsw, regvfile_name, core_prefix)

if __name__ == "__main__" : main ()
