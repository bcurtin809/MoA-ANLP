import json
import datasets
from fire import Fire
from functools import partial
from typing import List
from loguru import logger

from utils import (
    generate_together,
    generate_openai,
    generate_with_aggregated_reference,
    generate_aggregated_reference,
    DEBUG,
)


def process_fn(
    item,
    model,
    reference_models=[],
    temperature=0.7,
    max_tokens=2048,
    rounds=1,
    provider="together",
):

    if provider == "together":
        generate_fn = generate_together
    elif provider == "openai":
        generate_fn = generate_openai
    else:
        assert False

    messages = [{"role": "user", "content": item["text"]}]

    references = item.get("references", [])
    
    prev_references = ""

    if len(references) == 0 and len(reference_models) > 0:

        for i_round in range(rounds):

            if DEBUG:
                logger.info(
                    f"Round {i_round+1}/{rounds} to collecting reference responses."
                )

            references = []

            for reference_model in reference_models:

                reference = generate_with_aggregated_reference(
                    model=reference_model,
                    messages=messages,
                    references=prev_references,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    generate_fn=generate_fn,
                )

                if reference is not None:

                    references.append(reference)
                    
            prev_references = generate_aggregated_reference(
                #model=model,
                #TODO change model to the aggregated model we want
                # Model Links https://api.together.xyz/models
                # test 1 (larger model) = META LLAMA 3 8B INSTRUCT TURBO - meta-llama/Meta-Llama-3.1-8B-Instruct-Turbo
                # test 2 (control for our fine-tune)= META LLAMA 3.2 3B INSTRUCT TURBO - meta-llama/Llama-3.2-3B-Instruct-Turbo-lora
                # test 3 (our fine-tuned model)= our llama 3.2 3B Fine-Tuned
                model="meta-llama/Llama-3.2-3B-Instruct-Turbo-lora",
                messages=messages,
                references=references,
                generate_fn=generate_fn,
            )

            references = []

    output = generate_with_aggregated_reference(
        model=model,
        messages=messages,
        references=prev_references,
        generate_fn=generate_fn,
    )

    return {
        "text": output,
    }


def main(
    model: str,
    output_path: str,
    reference_paths: str = None,
    reference_models: str = None,
    temperature: float = 0.7,
    max_tokens: int = 2048,
    rounds: int = 1,
    num_proc: int = 16,
    provider: str = "together",
):

    if reference_paths is None:
        reference_paths = []
    else:
        reference_paths = reference_paths.split(",")

    if reference_models is None:
        reference_models = []
    else:
        reference_models = reference_models.split(",")

    eval_set = []
    with open("FLASK/evaluation_set/flask_evaluation.jsonl") as f:
        for line in f:
            if line.strip() == "":
                continue
            item = json.loads(line)
            eval_set.append({"question_id": item["idx"], "text": item["instruction"]})

    eval_set = datasets.Dataset.from_list(eval_set)

    if len(reference_paths):

        logger.info(f"`reference_paths` provided: {reference_paths}")

        references = []
        for reference_path in reference_paths:
            with open(reference_path) as f:
                reference_responses = json.load(f)
                logger.info(
                    f"Reading reference outputs: {reference_path} ({len(reference_responses)})"
                )
                for i_reference_response, reference_response in enumerate(
                    reference_responses
                ):
                    if len(references) <= i_reference_response:
                        references.append([reference_response["output"]])
                    else:
                        references[i_reference_response].append(
                            reference_response["output"]
                        )

        eval_set = eval_set.add_column(f"references", references)

    elif len(reference_models):

        logger.info(
            f"`reference_models` provided: {reference_models}. Will generate reference responses on-the-fly."
        )

    logger.info(f"Start.")

    eval_set = eval_set.map(
        partial(
            process_fn,
            model=model,
            reference_models=reference_models,
            temperature=temperature,
            max_tokens=max_tokens,
            rounds=rounds,
            provider=provider,
        ),
        batched=False,
        num_proc=num_proc,
    )

    logger.info(f"Saving outputs to {output_path}.")

    eval_set.to_json(output_path)


if __name__ == "__main__":

    Fire(main)
