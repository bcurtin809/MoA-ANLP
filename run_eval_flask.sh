
trap "trap - SIGTERM && kill -- -$$" SIGINT SIGTERM EXIT

export DEBUG=0

mkdir -p outputs/flask

python generate_for_flask.py \
    --model="Qwen/Qwen2.5-72B-Instruct-Turbo" \
    --output-path="outputs/flask/Qwen2.5-72B-Instruct-Turbo-round-1-test-1.jsonl" \
    --reference-models="microsoft/WizardLM-2-8x22B,Qwen/Qwen2-72B-Instruct,Qwen/Qwen2.5-72B-Instruct-Turbo,meta-llama/Llama-3-70b-chat-hf,mistralai/Mixtral-8x22B-Instruct-v0.1,databricks/dbrx-instruct" \
    --rounds 1 \
    --num-proc 16

cd FLASK/gpt_review

python gpt4_eval.py \
    -a '../../outputs/flask/Qwen2.5-72B-Instruct-Turbo-round-1-test-1.jsonl' \
    -o '../../outputs/flask/chatgpt_review-test-1.jsonl'

python aggregate_skill.py -m '../../outputs/flask/chatgpt_review-test-1.jsonl'

cat outputs/stats/chatgpt_review_skill-ours-test-1.csv