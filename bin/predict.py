#!/usr/bin/python3

from Bio import SeqIO
import numpy as np
import pandas as pd
import csv
from featuresetup_module import transcript_info, transcript_info_dict
from sklearn.externals import joblib
from sklearn import preprocessing
from sklearn.ensemble import GradientBoostingClassifier
import argparse
from os.path import splitext, basename, join, exists
import os

####################################################
# Import fasta, cpat, diamond files from cmnd line #
####################################################

# function to test if output directory string is a directory
def dir_path(string):
    if os.path.isdir(string):
        return string
    else:
        raise NotADirectoryError(string)

usage = "usage: %prog [options] -f transcript.fa -c cpat.csv -d diamond.out"

parser = argparse.ArgumentParser(description="predict lncRNAs from transcript sequences")
parser.add_argument("-f", "--fasta", dest="trans_fasta", required=True, metavar="transcript.fa", help="fasta file of transcript sequences for prediction")
parser.add_argument("-c", "--cpat_out", dest="cpat_out", required=True, metavar="cpat_out.csv", help="CPAT output of transcript sequences")
parser.add_argument("-d", "--diamond_out", dest="diam_out", required=True, metavar="diamond_out.tab", help="Diamond output of transcript sequences")
parser.add_argument("-s", "--score_cutoff", dest="score_cut", type=float, default=0.5, metavar="s", help="Minimum cutoff score for the lncRNA prediction (Default: 0.5)")
parser.add_argument("-o", "--outDir", dest = "outDir",
        required = False, metavar = "Output directory location",
        type = dir_path, help = "Location to put the output files")

args = parser.parse_args()

## Grab pickles from directory where this file is stored 
CURRENT_DIR = os.path.dirname(__file__)

#path of the inputfiles
fasta_path = os.path.dirname(args.trans_fasta)

"""set path of outputs to the location of the input fasta
if no output directory (-o, --outDir) is specified"""
if args.outDir == 0:
    out = fasta_path
else:
    out = args.outDir

#os.path.join(CURRENT_DIR+'../gb_models
clf1 = joblib.load(os.path.join(CURRENT_DIR+'/../updated_gb_models/model1.pkl'))
clf2 = joblib.load(os.path.join(CURRENT_DIR+'/../updated_gb_models/model2.pkl')) 
clf3 = joblib.load(os.path.join(CURRENT_DIR+'/../updated_gb_models/model3.pkl')) 
clf4 = joblib.load(os.path.join(CURRENT_DIR+'/../updated_gb_models/model4.pkl')) 
clf5 = joblib.load(os.path.join(CURRENT_DIR+'/../updated_gb_models/model5.pkl')) 
clf6 = joblib.load(os.path.join(CURRENT_DIR+'/../updated_gb_models/model6.pkl')) 
clf7 = joblib.load(os.path.join(CURRENT_DIR+'/../updated_gb_models/model7.pkl')) 
clf8 = joblib.load(os.path.join(CURRENT_DIR+'/../updated_gb_models/model8.pkl')) 

trans_info, trans_dict, trans_names = transcript_info_dict(args.trans_fasta, args.cpat_out, args.diam_out)

key_order= ["align_perc_len", "align_perc_ORF", "align_length", "ORF", "length", "GC", "fickett", "hexamer", "identity"] # to keep this order 

trans_dict_order = {gene:{feature:trans_dict[gene][feature] for feature in key_order} for gene in trans_names} 

# changed this from trans_dict to trans_dict_order
trans_array = np.array([[trans_dict_order[gene][feature] for feature in sorted(trans_dict_order[gene])] for gene in trans_names], dtype=float)

trans_n = preprocessing.normalize(trans_array, norm='l2')

model_col_names = ['Model1', 'Model2', 'Model3', 'Model4', 'Model5', 'Model6', 'Model7', 'Model8']
prediction = pd.DataFrame(index = trans_names, columns = model_col_names)
probability = pd.DataFrame(index = trans_names, columns = model_col_names) 

model_names = [clf1, clf2, clf3, clf4, clf5, clf6, clf7, clf8]
count = 1

for x in model_names:
    model_name = 'Model' + str(count)
#    print(model_name)
    count = count + 1
    pred = x.predict(trans_n)
    prob = x.predict_proba(trans_n)
    lnc_score = prob[:,1]
#    print(probability)
    probability[model_name] = lnc_score.tolist()
    prediction[model_name] = pred.tolist()

prediction.to_csv(os.path.join(out,"all_model_predictions.csv"), sep=",")
probability.to_csv(os.path.join(out,"all_model_scores.csv"), sep=",")


## Run logistic regression in R on model scores
CURRENT_DIR = os.path.dirname(__file__)
path_to_Rscript = os.path.join(CURRENT_DIR+'/log_reg.R')
cmnd_to_run = 'Rscript ' + path_to_Rscript + ' -m ' + os.path.join(out, "all_model_predictions.csv") + ' -t GB'
os.system(cmnd_to_run)

# empty pandas df 
#logreg_col_names = ['trans_name', 'length', 'ORF', 'GC', 'fickett', 'hexamer', 'identity', 'align_len', 'align_len_perc', 'align_orf_perc', 'score', 'prediction']
#log_reg = pd.DataFrame(index = trans_names, columns = logreg_col_names)

# create pandas df with all features and log reg output
# add to trans_dict?

with open(os.path.join(out,"ensemble_logreg_pred.csv")) as pred:
    pred_reader = csv.reader(pred, delimiter = ",")
    next(pred_reader) 
    for row in pred_reader:
        name = row[0]
        name = name.lower()
        score = row[1]
        trans_dict[name]["lnc_score"] = score
        if float(score) >= args.score_cut:
            trans_dict[name]["prediction"] = 1
        else:
            trans_dict[name]["prediction"] = 0  

feature_df = pd.DataFrame.from_dict(trans_dict, orient='index')
feature_df = feature_df[['length', 'ORF', 'GC', 'fickett', 'hexamer', 'identity', 'align_length', 'align_perc_len', 'align_perc_ORF', 'lnc_score', 'prediction']]

# count number of predicted lncRNAs:
lnc_num = sum(x == 1 for x in feature_df['prediction'])

feature_df.to_csv(os.path.join(out, "final_ensemble_predictions.csv"), sep=",")

print("Run successful!")
print("There were " + str(lnc_num) + " lncRNAs predicted from " + args.trans_fasta)
