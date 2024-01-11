#!/usr/bin/env python3
import caikit_nlp
import argparse


def main():
    parser = argparse.ArgumentParser(prog="convert.py")
    parser.add_argument(
        "--model-path",
        help='Path of the base HuggingFace model. If the ALLOW_DOWNLOADS env var is set, this can be a HuggingFace hub model e.g. "google/flan-t5-small"',
    )
    parser.add_argument(
        "--model-save-path", help="Path to save the Caikit format model to"
    )

    args = parser.parse_args()

    model = caikit_nlp.text_generation.TextGeneration.bootstrap(args.model_path)

    model.save(model_path=args.model_save_path)


if __name__ == "__main__":
    main()
