# evaluation.py
# ─────────────────────────────────────────────────────────────
# PIPELINE EVALUATION FRAMEWORK
# Runs multiple prompts through the full pipeline
# and measures reliability metrics.
# ─────────────────────────────────────────────────────────────

import time

from main import run_pipeline


# ─────────────────────────────────────────────────────────────
# TEST DATASET
# ─────────────────────────────────────────────────────────────

REAL_WORLD_PROMPTS = [
    "Build a CRM with login and analytics",
    "Build a hospital management system",
    "Build a task manager with users and tasks",
    "Build an e-commerce backend with products and orders",
    "Build a chat application with authentication",
    "Build a learning management system",
    "Build a food delivery platform",
    "Build a booking system for hotels",
    "Build a payroll management app",
    "Build a project management tool"
]

EDGE_CASE_PROMPTS = [
    "Build something cool",
    "I want a dashboard maybe",
    "Users but no login",
    "Build app",
    "Something for healthcare",
    "Use blockchain and AI and social media together",
    "Admins but no users",
    "Payments without products",
    "Fast app with everything",
    ""
]

ALL_PROMPTS = REAL_WORLD_PROMPTS + EDGE_CASE_PROMPTS


# ─────────────────────────────────────────────────────────────
# MAIN EVALUATION LOOP
# ─────────────────────────────────────────────────────────────

def run_evaluation():
    """
    Runs all prompts through the full pipeline and
    computes evaluation metrics.
    """

    print("\n" + "=" * 70)
    print("PIPELINE EVALUATION FRAMEWORK")
    print("=" * 70)

    total = len(ALL_PROMPTS)

    passed = 0
    failed = 0

    total_repairs = 0
    total_latency = 0

    results = []

    for idx, prompt in enumerate(ALL_PROMPTS, start=1):

        print("\n" + "-" * 70)
        print(f"[Test {idx}/{total}]")
        print(f"Prompt: {prompt}")
        print("-" * 70)

        start = time.time()

        try:
            result = run_pipeline(prompt)

            latency = round(time.time() - start, 2)

            success = result.evaluation.get("overall_success", False)

            repairs = len(result.repairs_made)

            if success:
                passed += 1
            else:
                failed += 1

            total_repairs += repairs
            total_latency += latency

            results.append({
                "prompt": prompt,
                "success": success,
                "repairs": repairs,
                "latency": latency,
            })

            print(f"\nResult: {'PASSED' if success else 'FAILED'}")
            print(f"Latency: {latency}s")
            print(f"Repairs: {repairs}")

        except Exception as e:

            failed += 1

            latency = round(time.time() - start, 2)

            results.append({
                "prompt": prompt,
                "success": False,
                "repairs": 0,
                "latency": latency,
                "error": str(e),
            })

            print(f"\nCRASHED: {e}")

    # ─────────────────────────────────────────────────────────
    # FINAL METRICS
    # ─────────────────────────────────────────────────────────

    success_rate = round((passed / total) * 100, 2)

    avg_repairs = round(total_repairs / total, 2)

    avg_latency = round(total_latency / total, 2)

    print("\n" + "=" * 70)
    print("FINAL EVALUATION REPORT")
    print("=" * 70)

    print(f"Total Prompts:      {total}")
    print(f"Passed:             {passed}")
    print(f"Failed:             {failed}")
    print(f"Success Rate:       {success_rate}%")
    print(f"Average Repairs:    {avg_repairs}")
    print(f"Average Latency:    {avg_latency}s")

    print("\nDetailed Results:")

    for r in results:
        print(
            f"  - Success={r['success']} | "
            f"Repairs={r['repairs']} | "
            f"Latency={r['latency']}s | "
            f"Prompt='{r['prompt']}'"
        )


# ─────────────────────────────────────────────────────────────
# ENTRYPOINT
# ─────────────────────────────────────────────────────────────

if __name__ == "__main__":
    run_evaluation()