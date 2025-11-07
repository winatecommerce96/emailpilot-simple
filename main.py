#!/usr/bin/env python3
"""
EmailPilot Simple - CLI Entry Point

Command-line interface for the simplified calendar generation workflow.

Usage:
    python main.py --client rogue-creamery --start-date 2025-01-01 --end-date 2025-01-31
    python main.py -c rogue-creamery -s 2025-01-01 -e 2025-01-31 --output-dir ./outputs
    python main.py -c rogue-creamery -s 2025-01-01 -e 2025-01-31 --stage 1
"""

import argparse
import asyncio
import logging
import os
import sys
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

from tools import CalendarTool, CalendarValidator
from agents.calendar_agent import CalendarAgent
from data.mcp_client import MCPClient
from data.rag_client import RAGClient
from data.firestore_client import FirestoreClient
from data.mcp_cache import MCPCache
from data.secret_manager_client import SecretManagerClient


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)


def parse_args():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description='EmailPilot Simple - Calendar Generation Workflow',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run full workflow
  python main.py --client rogue-creamery --start-date 2025-01-01 --end-date 2025-01-31

  # Save outputs to specific directory
  python main.py -c rogue-creamery -s 2025-01-01 -e 2025-01-31 --output-dir ./outputs

  # Run specific stage only (for testing)
  python main.py -c rogue-creamery -s 2025-01-01 -e 2025-01-31 --stage 1

  # Skip output validation
  python main.py -c rogue-creamery -s 2025-01-01 -e 2025-01-31 --no-validate
        """
    )

    # Required arguments
    parser.add_argument(
        '-c', '--client',
        required=True,
        help='Client name/slug (e.g., "rogue-creamery")'
    )
    parser.add_argument(
        '-s', '--start-date',
        required=True,
        help='Start date in YYYY-MM-DD format'
    )
    parser.add_argument(
        '-e', '--end-date',
        required=True,
        help='End date in YYYY-MM-DD format'
    )

    # Optional arguments
    parser.add_argument(
        '-o', '--output-dir',
        help='Directory to save workflow outputs (default: ./outputs)'
    )
    parser.add_argument(
        '--no-validate',
        action='store_true',
        help='Skip output validation'
    )
    parser.add_argument(
        '--stage',
        type=int,
        choices=[1, 2, 3],
        help='Run specific stage only (1=Planning, 2=Structuring, 3=Briefs)'
    )
    parser.add_argument(
        '--no-save',
        action='store_true',
        help='Do not save outputs to files'
    )
    parser.add_argument(
        '--model',
        default='claude-sonnet-4-5-20250929',
        help='Claude model to use (default: claude-sonnet-4-5-20250929)'
    )
    parser.add_argument(
        '--prompts-dir',
        help='Path to prompts directory (default: ./prompts)'
    )

    return parser.parse_args()


def load_config():
    """Load configuration from environment variables."""
    config = {
        'anthropic_api_key': os.getenv('ANTHROPIC_API_KEY'),
        'google_cloud_project': os.getenv('GOOGLE_CLOUD_PROJECT'),
    }

    # Validate required environment variables
    missing = [key for key, value in config.items() if not value]
    if missing:
        logger.error(f"Missing required environment variables: {', '.join(missing)}")
        logger.error("Please set the following environment variables:")
        for key in missing:
            logger.error(f"  - {key.upper()}")
        sys.exit(1)

    return config


def initialize_components(config: dict, args: argparse.Namespace):
    """
    Initialize all workflow components.

    Args:
        config: Configuration dictionary from environment
        args: Parsed command-line arguments

    Returns:
        Initialized CalendarTool instance
    """
    logger.info("Initializing workflow components...")

    # Initialize data layer clients
    logger.info("Initializing data layer clients...")

    secret_manager_client = SecretManagerClient(
        project_id=config['google_cloud_project']
    )

    mcp_client = MCPClient(
        secret_manager_client=secret_manager_client
    )

    rag_client = RAGClient(
        rag_base_path='/Users/Damon/klaviyo/klaviyo-audit-automation/emailpilot-orchestrator/rag'
    )

    firestore_client = FirestoreClient(
        project_id=config['google_cloud_project']
    )

    cache = MCPCache()

    logger.info("Data layer clients initialized")

    # Initialize Calendar Agent
    logger.info(f"Initializing CalendarAgent with model: {args.model}")

    calendar_agent = CalendarAgent(
        anthropic_api_key=config['anthropic_api_key'],
        mcp_client=mcp_client,
        rag_client=rag_client,
        firestore_client=firestore_client,
        cache=cache,
        model=args.model,
        prompts_dir=args.prompts_dir
    )

    logger.info("CalendarAgent initialized")

    # Initialize Calendar Tool
    output_dir = args.output_dir or './outputs'
    validate_outputs = not args.no_validate

    calendar_tool = CalendarTool(
        calendar_agent=calendar_agent,
        output_dir=output_dir,
        validate_outputs=validate_outputs
    )

    logger.info("CalendarTool initialized")
    logger.info("All components ready")

    return calendar_tool


async def run_full_workflow(
    calendar_tool: CalendarTool,
    client_name: str,
    start_date: str,
    end_date: str,
    save_outputs: bool
):
    """
    Run the complete three-stage workflow.

    Args:
        calendar_tool: Initialized CalendarTool
        client_name: Client slug
        start_date: Start date (YYYY-MM-DD)
        end_date: End date (YYYY-MM-DD)
        save_outputs: Whether to save outputs to files

    Returns:
        Exit code (0 for success, 1 for failure)
    """
    logger.info("="*80)
    logger.info(f"Running full workflow for {client_name}")
    logger.info(f"Date range: {start_date} to {end_date}")
    logger.info("="*80)

    try:
        result = await calendar_tool.run_workflow(
            client_name=client_name,
            start_date=start_date,
            end_date=end_date,
            save_outputs=save_outputs
        )

        # Print results
        print("\n" + "="*80)
        print("WORKFLOW RESULTS")
        print("="*80)

        if result.get('success'):
            print("\n✅ Workflow completed successfully!")

            # Print validation summary
            validation = result.get('validation', {})
            print("\nValidation Summary:")
            print(f"  - Planning: {'✅ Valid' if validation.get('planning_valid') else '⚠️  Has warnings'}")
            print(f"  - Calendar: {'✅ Valid' if validation.get('calendar_valid') else '❌ Invalid'}")
            print(f"  - Briefs: {'✅ Valid' if validation.get('briefs_valid') else '⚠️  Has warnings'}")

            if validation.get('warnings'):
                print(f"\nWarnings ({len(validation['warnings'])}):")
                for warning in validation['warnings']:
                    print(f"  ⚠️  {warning}")

            # Print campaign count
            campaigns = result.get('calendar_json', {}).get('campaigns', [])
            print(f"\nGenerated {len(campaigns)} campaigns")

            return 0

        else:
            print("\n❌ Workflow failed")

            # Print error details
            if result.get('error'):
                print(f"\nError: {result['error']}")

            validation = result.get('validation', {})
            if validation.get('input_errors'):
                print("\nInput Validation Errors:")
                for error in validation['input_errors']:
                    print(f"  ❌ {error}")

            if validation.get('errors'):
                print(f"\nValidation Errors ({len(validation['errors'])}):")
                for error in validation['errors']:
                    print(f"  ❌ {error}")

            return 1

    except Exception as e:
        logger.error(f"Workflow failed with exception: {str(e)}", exc_info=True)
        print(f"\n❌ Workflow failed: {str(e)}")
        return 1


async def run_single_stage(
    calendar_tool: CalendarTool,
    stage: int,
    client_name: str,
    start_date: str,
    end_date: str
):
    """
    Run a single workflow stage.

    Args:
        calendar_tool: Initialized CalendarTool
        stage: Stage number (1, 2, or 3)
        client_name: Client slug
        start_date: Start date (YYYY-MM-DD)
        end_date: End date (YYYY-MM-DD)

    Returns:
        Exit code (0 for success, 1 for failure)
    """
    logger.info("="*80)
    logger.info(f"Running Stage {stage} only for {client_name}")
    logger.info(f"Date range: {start_date} to {end_date}")
    logger.info("="*80)

    try:
        # For stages 2 and 3, we need outputs from previous stages
        kwargs = {}

        if stage == 2:
            print("\n⚠️  Stage 2 requires planning output from Stage 1")
            print("Please run Stage 1 first and provide the planning output")
            return 1

        if stage == 3:
            print("\n⚠️  Stage 3 requires calendar JSON from Stage 2")
            print("Please run Stage 2 first and provide the calendar JSON")
            return 1

        result = await calendar_tool.run_stage(
            stage=stage,
            client_name=client_name,
            start_date=start_date,
            end_date=end_date,
            **kwargs
        )

        # Print results
        print("\n" + "="*80)
        print(f"STAGE {stage} RESULTS")
        print("="*80)

        if result.get('success'):
            print(f"\n✅ Stage {stage} completed successfully!")

            output = result.get('output')
            if isinstance(output, str):
                print(f"\nOutput length: {len(output)} characters")
                print("\nOutput preview:")
                print(output[:500] + "..." if len(output) > 500 else output)
            else:
                print(f"\nOutput type: {type(output)}")

            return 0

        else:
            print(f"\n❌ Stage {stage} failed")
            if result.get('error'):
                print(f"\nError: {result['error']}")
            return 1

    except Exception as e:
        logger.error(f"Stage {stage} failed with exception: {str(e)}", exc_info=True)
        print(f"\n❌ Stage {stage} failed: {str(e)}")
        return 1


async def main():
    """Main entry point."""
    args = parse_args()

    print("="*80)
    print("EmailPilot Simple - Calendar Generation Workflow")
    print("="*80)

    # Load configuration
    config = load_config()

    # Initialize non-async clients
    logger.info("Initializing workflow components...")
    logger.info("Initializing data layer clients...")

    secret_manager_client = SecretManagerClient(
        project_id=config['google_cloud_project']
    )

    rag_client = RAGClient(
        rag_base_path='/Users/Damon/klaviyo/klaviyo-audit-automation/emailpilot-orchestrator/rag'
    )

    firestore_client = FirestoreClient(
        project_id=config['google_cloud_project']
    )

    cache = MCPCache()

    # Use async context manager for MCPClient
    async with MCPClient(secret_manager_client=secret_manager_client) as mcp_client:
        logger.info("Data layer clients initialized")

        # Initialize Calendar Agent
        logger.info(f"Initializing CalendarAgent with model: {args.model}")

        calendar_agent = CalendarAgent(
            anthropic_api_key=config['anthropic_api_key'],
            mcp_client=mcp_client,
            rag_client=rag_client,
            firestore_client=firestore_client,
            cache=cache,
            model=args.model,
            prompts_dir=args.prompts_dir
        )

        logger.info("CalendarAgent initialized")

        # Initialize Calendar Tool
        output_dir = args.output_dir or './outputs'
        validate_outputs = not args.no_validate

        calendar_tool = CalendarTool(
            calendar_agent=calendar_agent,
            output_dir=output_dir,
            validate_outputs=validate_outputs
        )

        logger.info("CalendarTool initialized")
        logger.info("All components ready")

        # Run workflow
        save_outputs = not args.no_save

        if args.stage:
            # Run single stage
            exit_code = await run_single_stage(
                calendar_tool=calendar_tool,
                stage=args.stage,
                client_name=args.client,
                start_date=args.start_date,
                end_date=args.end_date
            )
        else:
            # Run full workflow
            exit_code = await run_full_workflow(
                calendar_tool=calendar_tool,
                client_name=args.client,
                start_date=args.start_date,
                end_date=args.end_date,
                save_outputs=save_outputs
            )

    print("\n" + "="*80)
    print("Workflow execution complete")
    print("="*80 + "\n")

    sys.exit(exit_code)


if __name__ == '__main__':
    asyncio.run(main())
