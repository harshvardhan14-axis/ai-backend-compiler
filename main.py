from schemas import PipelineOutput
from generator import extract_intent, generate_database, generate_api
from validator import validate_all
from repair import repair_all
from runtime import run_simulation


def run_pipeline(user_prompt: str) -> PipelineOutput:
    """
    Runs the complete AI pipeline end-to-end.
    """

    print("\n" + "=" * 60)
    print("[Pipeline] Starting AI Backend Generator")
    print("=" * 60)

    print("\n[Stage 1] Extracting intent...")

    intent = extract_intent(user_prompt)

    print(f"  App Name: {intent.app_name}")
    print(f"  App Type: {intent.app_type}")
    print(f"  Entities: {intent.entities}")
    print(f"  Features: {intent.features}")


    print("\n[Stage 2] Generating database schema...")

    database = generate_database(intent)

    print(f"  Generated {len(database.tables)} table(s)")

    for table in database.tables:
        cols = [col.name for col in table.columns]
        print(f"    - {table.table_name}: {cols}")


    print("\n[Stage 3] Generating API schema...")

    api = generate_api(intent, database)

    print(f"  Generated {len(api.endpoints)} endpoint(s)")

    for endpoint in api.endpoints:
        print(f"    - {endpoint.method} {endpoint.path}")


    print("\n[Stage 4] Validating generated schemas...")

    validation_report = validate_all(database, api)

    if validation_report["passed"]:
        print("  Validation PASSED")
    else:
        print("  Validation FAILED")

        for error in validation_report["errors"]:
            print(f"    ERROR: {error}")


    print("\n[Stage 5] Repairing schemas if necessary...")

    database, api, repairs_made = repair_all(
        database,
        api,
        validation_report
    )

    if repairs_made:
        print(f"  Repairs made: {len(repairs_made)}")

        for repair in repairs_made:
            print(f"    - {repair}")
    else:
        print("  No repairs needed")


    print("\n[Stage 6] Running runtime simulation...")

    simulation = run_simulation(
        intent,
        database,
        api,
        repairs_made
    )

    print("\n[Pipeline] Simulation Summary")
    print(f"  {simulation['summary']}")


    final_output = PipelineOutput(
        intent=intent,
        database=database,
        api=api,
        validation_passed=validation_report["passed"],
        repairs_made=repairs_made,
        simulation_result=simulation["summary"],
        evaluation=simulation["evaluation"],
    )

    print("\n" + "=" * 60)
    print("[Pipeline] Finished Successfully")
    print("=" * 60)

    return final_output


if __name__ == "__main__":

    sample_prompt = (
        "Build a task management REST API with users and tasks "
        "where users can create, update, and delete tasks"
    )

    result = run_pipeline(sample_prompt)

    print("\n[Final Evaluation Metrics]")

    for key, value in result.evaluation.items():
        print(f"  {key}: {value}")