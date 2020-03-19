#!/usr/bin/env python

import os
import argparse
import subprocess
import json
from os.path import isfile, join, basename
import time
import pandas as pd 
from datetime import datetime
import tempfile

import sys
sys.path.append(
    os.path.abspath(os.path.join(os.path.dirname(__file__), os.path.pardir, 'instance_generator')))
import route_gen

def main():
    '''
    The algorithm for benchmark works as follow:
        For a certain number of iteration:
            generate instance with default generator value
            for each encoding inside subfolders of encoding (one folder for each encoding):
                start timer
                solve with clyngo
                stop timer
                test solution:
                    if legal
                        add time in a csv (S)
                    else:
                        add int max as time
                        print an error message
    '''
    parser = argparse.ArgumentParser(description='Benchmark ! :D')
    parser.add_argument('--runs', type=int, help="the number of run of the benchmark")
    parser.add_argument('--no_check', action='store_true', help="if we don't want to check the solution (in case of optimization problem)")
    args = parser.parse_args()
    number_of_run = args.runs
    print("Start of the benchmarks")
    encodings = [x for x in os.listdir("../encoding/")]
    print("Encodings to test:")
    for encoding in encodings:
        print("\t-{}".format(encoding))
    results = []
    costs_run = []
    for i in range(number_of_run):
        print("Iteration {}".format(i + 1))
        result_iteration = dict()
        cost_iteration = dict()
        instance, minimal_cost = route_gen.instance_generator()
        # we get the upper bound of the solution generated by the generator
        cost_iteration["upper_bound"] = minimal_cost
        instance_temp = tempfile.NamedTemporaryFile(mode="w+", suffix='.lp', dir=".", delete=False)
        instance_temp.write(repr(instance))
        for encoding in encodings:
            print("Encoding {}:".format(encoding))
            files_encoding = ["../encoding/" + encoding + "/" + f for f in os.listdir("../encoding/" + encoding) if isfile(join("../encoding/" + encoding, f))]
            start = time.time()
            clingo = subprocess.Popen(["clingo"] + files_encoding + [basename(instance_temp.name)] + ["--outf=2"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            (stdoutdata, stderrdata) = clingo.communicate()
            clingo.wait()
            end = time.time()
            duration = end - start
            #print("out: {}".format(stdoutdata))
            #print("error: {}".format(stderrdata))
            #print(stdoutdata)
            json_answers = json.loads(stdoutdata)

            #call = json_answers["Call"][-1]
            #answer = call["Witnesses"][-1]
            #cost = answer["Costs"][0]

            correct_solution = json_answers["Result"] == "SATISFIABLE" or json_answers["Result"] == "OPTIMUM FOUND"
            cost = float('inf')
            call = json_answers["Call"][-1]
            answer = call["Witnesses"][-1]
            # we need to check all solution and get the best one
            for call_current in json_answers["Call"]:
                if "Witnesses" in call_current:
                    answer_current = call_current["Witnesses"][-1]
                    current_cost = answer_current["Costs"][0]
                    if current_cost < cost:
                        answer = answer_current
                        cost = current_cost
            # if it's not an intermediate call (needed for incremental grouding)
            if not args.no_check:
                # we append "" just to get the last . when we join latter
                answer = answer["Value"] + [""]
                answer_str = ".".join(answer)
                answer_temp = tempfile.NamedTemporaryFile(mode="w+", suffix='.lp', dir=".", delete=False)
                answer_temp.write(answer_str)
                clingo_check = subprocess.Popen(["clingo"] + ["../test_solution/test_solution.lp"] + [basename(answer_temp.name)] + [basename(instance_temp.name)] + ["--outf=2"] + ["-q"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                (stdoutdata_check, stderrdata_check) = clingo_check.communicate()
                #print("stdoudata check : {}".format(stdoutdata_check))
                json_check = json.loads(stdoutdata_check)
                answer_temp.close()
                os.remove(answer_temp.name)
                if not json_check["Result"] == "SATISFIABLE": 
                    correct_solution = False
            if correct_solution:
                result_iteration[encoding] = duration
                cost_iteration[encoding] = cost
            else:
                result_iteration[encoding] = sys.maxsize
                cost_iteration[encoding] = float("inf")
            print("\tSatisfiable {}".format(correct_solution))
            print("\tDuration {} seconds".format(result_iteration[encoding]))
            print("\tBest solution {}".format(cost))
            print("\tUpper bound {}".format(minimal_cost))
        results.append(result_iteration)
        costs_run.append(cost_iteration)
        instance_temp.close()
        os.remove(instance_temp.name)
    df = pd.DataFrame(results)
    now = datetime.now()
    date_string = now.strftime("%d_%m_%Y_%H_%M_%S")
    df.to_csv("results/" + date_string + ".csv")
    # we also print the cost
    df = pd.DataFrame(costs_run)
    df.to_csv("results/" + date_string + "_costs.csv")


if __name__== "__main__":
      main()