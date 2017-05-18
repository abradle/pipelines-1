#!/usr/bin/env python

# Copyright 2017 Informatics Matters Ltd.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import argparse
import os
import subprocess
from multiprocessing.dummy import Pool as ThreadPool
from rdkit import Chem
from src.python.utils import utils
import tempfile
import threading
lock = threading.Lock()
PDB_PATH = ""
WRITER = ""
COUNTER = 0
SUCCESS = 0

def run_and_get_ans(mol):
    global PDB_PATH
    smogmol = tempfile.NamedTemporaryFile("w",delete=True).name
    out_f = open(smogmol, "w")
    out_f.write(Chem.MolToMolBlock(mol))
    out_f.close()
    # Run command
    proc = subprocess.Popen(["/usr/local/SMoG2016_Rev1/SMoG2016.exe", PDB_PATH, smogmol, "DeltaG"],
                            stdout=subprocess.PIPE)
    # Parse the output
    me = proc.stdout.read()
    if not me:
        # TODO - shouldn't we fail instead?
        return None
    answer = float(me.split("DeltaG")[1].strip())
    return answer

def run_dock(mol):
    global COUNTER
    global SUCCESS
    answer = run_and_get_ans(mol)
    if answer is None:
        utils.log("FAILED MOL", Chem.MolToSmiles(mol))
    else:
        mol.SetDoubleProp("SMoG2016_SCORE", answer)
        utils.log("SCORED MOL:", Chem.MolToSmiles(mol), answer)
        # Write ligand
        lock.acquire()
        SUCCESS+=1
        WRITER.write(mol)
        WRITER.flush()
        lock.release()
    COUNTER+=1

def main():
    global WRITER
    global PDB_PATH
    parser = argparse.ArgumentParser(description='SMoG2016 - Docking calculation.')
    utils.add_default_io_args(parser)
    parser.add_argument('--no-gzip', action='store_true', help='Do not compress the output (STDOUT is never compressed')
    parser.add_argument('-pdb', '--pdb_file', help="PDB file for scoring")
    args = parser.parse_args()

    smog_path = "/usr/local/SMoG2016_Rev1/"
    PDB_PATH = args.pdb_file
    # Open up the input file
    input, suppl = utils.default_open_input(args.input, args.informat)
    # Open the ouput file

    output, WRITER, output_base = utils.default_open_output(args.output, "SMoG2016", args.outformat, compress=not args.no_gzip)

    # Cd to the route of the action
    os.chdir(smog_path)

    # Iterate over the molecules
    pool = ThreadPool(8)
    pool.map(run_dock, suppl)
    # Close the file
    WRITER.close()

    if args.meta:
        utils.write_metrics(output_base, {'__InputCount__': COUNTER, '__OutputCount__': SUCCESS, 'RxnMaker': SUCCESS})

if __name__ == "__main__":
    main()
