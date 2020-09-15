#!/usr/bin/python2.7
#
#    Build Latex tables of verilog module interface signals and registers
#

import sys
import os.path
import re

def write_mapping(outfile, name_map, width_map, init_val_map, type_map, regname):
    #write output file
    fout = open (outfile, 'w')

    fout.write("//This file was generated by script swreg2regmap.py\n\n")

    fout.write("//write registers\n")
    for i in range(len(name_map)):
        if (type_map[i] == "`W_TYP" or type_map[i] == "`RW_TYP"):
            fout.write("`REG_ARE(clk, rst, valid & wstrb & (addr == " + str(i) + "), " + str(init_val_map[i]) + ", " + str(name_map[i]) + ", wdata[" + str(width_map[i]) + "-1:0]);\n")
            pass
        pass
        
    fout.write("\n\n//read registers\n")
    fout.write("always @* begin\n")
    fout.write("   rdata = `DATA_W'd0;\n")
    fout.write("   case(addr)\n")
    for i in range(len(name_map)):
        if (type_map[i] == "`R_TYP" or type_map[i] == "`RW_TYP"):
            fout.write("     " + str(i) + ": rdata = " + str(name_map[i]) + " | `DATA_W'd0;\n")
            pass
        pass
    fout.write("     default: rdata = `DATA_W'd0;\n")
    fout.write("   endcase\n")
    fout.write("end\n")

    fout.close()
    return


def swreg_parse (program, outfile, regname) :
    name_map = []
    width_map = []
    init_val_map = []
    type_map = []
    for line in program :
        subline = re.sub('\[|\]|:|,|//|\;',' ', line)
        subline = re.sub('\(',' ',subline, 1)
        subline = re.sub('\)',' ', subline, 1)

        flds = subline.split()
        if not flds : continue #empty line
        #print flds[0]
        if ('SWREG_' in flds[0]): #software accessible registers
            reg_name = flds[1] #register name
            reg_width = flds[2] #register width
            reg_init_val = flds[3] #register init val

            #register type
            if '_RW' in flds[0]:
                reg_type = '`RW_TYP'
            elif 'W' in flds[1]:
                reg_type = '`W_TYP'
            else:
                reg_type = '`R_TYP'


            name_map.append(reg_name)
            width_map.append(reg_width)
            init_val_map.append(reg_init_val)
            type_map.append(reg_type)
        else: continue #not a recognized macro

    write_mapping(outfile, name_map, width_map, init_val_map, type_map, regname)
    return

def main () :
    #parse command line
    if len(sys.argv) != 4:
        vaError("Usage: ./v2tex.py infile outfile REG_NAME")
    else:
        infile = sys.argv[1]
        outfile = sys.argv[2]
        regname = sys.argv[3]
        
    #parse input file
    fin = open (infile, 'r')
    program = fin.readlines()
    fin.close()
    swreg_parse (program, outfile, regname)

if __name__ == "__main__" : main ()
