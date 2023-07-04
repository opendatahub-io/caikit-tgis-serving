#!/usr/bin/env python3

import caikit_nlp
import argparse

parser = argparse.ArgumentParser(prog="convert.py")
parser.add_argument("--model-path", help="Path of the base HuggingFace model", )
parser.add_argument("--model-save-path", help="Path to save the Caikit format model to")

args = parser.parse_args()

model = caikit_nlp.text_generation.TextGeneration.bootstrap(args.model_path)

model.save(model_path=args.model_save_path)