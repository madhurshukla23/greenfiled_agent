"""
Interactive Discovery Workshop CLI
Guides users through Azure Landing Zone discovery process
"""
import asyncio
import logging
from datetime import datetime
from typing import List, Optional
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.prompt import Prompt, Confirm
from rich.markdown import Markdown
from rich import box

from src.config import Config
from src.discovery_agent import DiscoveryAgent
from src.discovery_framework import (
    DiscoveryQuestion,
    DiscoveryCategory,
    InformationPriority,
    get_questions_by_category,
    get_critical_questions,
    DISCOVERY_QUESTIONS
)
from src.validators import ValidationSeverity
from src.architecture_visualizer import ArchitectureVisualizer
from src.interactive_helper import InteractiveHelper

console = Console()


class DiscoveryWorkshopCLI:
    """Interactive CLI for Azure Landing Zone Discovery Workshop"""
    
    def __init__(self):
        self.config = Config()
        self.agent = DiscoveryAgent(self.config)
        self.session_id = f"workshop_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        self.last_question = None  # Track last question for editing
        self.answers_this_session = []  # Track answers given this session
        self.helper = InteractiveHelper(self.agent)  # Interactive help system
    
    def find_latest_results(self) -> Optional[str]:
        """Find the most recent discovery results file"""
        import glob
        import os
        
        result_files = glob.glob("discovery_results_*.json")
        if not result_files:
            return None
        
        # Get the most recent file
        latest = max(result_files, key=os.path.getctime)
        return latest
    
    def show_welcome(self):
        """Display welcome message"""
        welcome_text = """
# 🎯 Azure Landing Zone Discovery Workshop

Welcome! This interactive workshop will help you gather all necessary information 
for a successful Azure Landing Zone deployment.

## How it works:
1. **Document Analysis**: We'll analyze uploaded documents in your blob storage
2. **Gap Identification**: Identify missing critical information
3. **Interactive Q&A**: You'll answer questions for gaps
4. **Summary Report**: Get a complete discovery report

## Interactive Commands:
Type **?help** at any prompt to see all available commands:
- `?list` - See all discovery questions
- `?naming` - Azure naming conventions
- `?ip-ranges` - IP address guidance
- `?costs` - Cost optimization tips
- `?progress` - Current progress
- And more!

Let's get started! 🚀
"""
        console.print(Panel(Markdown(welcome_text), border_style="cyan", expand=False))
    
    def show_configuration(self):
        """Display current Azure configuration"""
        table = Table(title="Azure Configuration", box=box.ROUNDED)
        table.add_column("Setting", style="cyan")
        table.add_column("Value", style="green")
        
        table.add_row("OpenAI Endpoint", self.config.azure_openai.endpoint)
        table.add_row("Deployment", self.config.azure_openai.deployment_name)
        table.add_row("Storage Container", self.config.azure_storage.container_name)
        table.add_row("Search Service", self.config.azure_search.endpoint)
        
        console.print(table)
        console.print()
    
    async def analyze_documents_step(self) -> int:
        """Step 1: Analyze uploaded documents"""
        console.print("\n[bold cyan]Step 1: Analyzing Documents[/bold cyan]")
        console.print("Scanning blob storage for requirement documents...\n")
        
        # Suppress search logging
        search_logger = logging.getLogger("src.search_client")
        original_level = search_logger.level
        search_logger.setLevel(logging.CRITICAL)
        
        try:
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console
            ) as progress:
                task = progress.add_task("Analyzing documents...", total=None)
                
                answers_found, documents = await self.agent.analyze_documents()
                
                progress.update(task, completed=True)
            
            # Show results
            if documents:
                console.print(f"\n[green]✓[/green] Analyzed {len(documents)} documents:")
                for doc in documents:
                    console.print(f"  • {doc}")
                console.print(f"\n[green]✓[/green] Extracted {answers_found} answers from documents\n")
            else:
                console.print("[yellow]⚠[/yellow] No documents found in blob storage")
                console.print("You can upload documents and re-run, or proceed with manual input.\n")
            
            return answers_found
            
        finally:
            search_logger.setLevel(original_level)
    
    def show_discovery_progress(self):
        """Display current discovery progress"""
        summary = self.agent.get_discovery_summary()
        
        # Overall progress
        console.print(Panel(
            f"[bold green]{summary['answered']}/{summary['total_questions']}[/bold green] questions answered "
            f"([cyan]{summary['completion_percentage']:.1f}%[/cyan] complete)",
            title="Discovery Progress",
            border_style="green"
        ))
        
        # Critical questions status
        critical = summary['critical_questions']
        console.print(f"\n[bold]Critical Information:[/bold] {critical['answered']}/{critical['total']} "
                     f"([cyan]{critical['percentage']:.1f}%[/cyan])")
        
        # Category breakdown
        table = Table(title="Progress by Category", box=box.SIMPLE)
        table.add_column("Category", style="cyan")
        table.add_column("Answered", justify="right")
        table.add_column("Total", justify="right")
        table.add_column("Progress", justify="right")
        
        for category, data in summary['by_category'].items():
            table.add_row(
                category,
                str(data['answered']),
                str(data['total']),
                f"{data['percentage']:.0f}%"
            )
        
        console.print("\n")
        console.print(table)
        console.print()
    
    async def ask_critical_questions(self):
        """Step 2: Ask user for missing critical information"""
        critical_gaps = self.agent.get_critical_gaps()
        
        if not critical_gaps:
            console.print("\n[green]✓[/green] All critical information gathered!\n")
            return
        
        console.print(f"\n[bold yellow]Step 2: Critical Information Needed[/bold yellow]")
        console.print(f"Found {len(critical_gaps)} critical questions that need answers.\n")
        
        for i, question in enumerate(critical_gaps, 1):
            await self._ask_single_question(question, i, len(critical_gaps))
    
    async def ask_questions_by_category(self, category: DiscoveryCategory):
        """Ask all missing questions for a specific category"""
        category_questions = get_questions_by_category(category)
        missing = [q for q in category_questions if q.id not in self.agent.session.answers]
        
        if not missing:
            console.print(f"\n[green]✓[/green] {category.value}: Complete!\n")
            return
        
        console.print(f"\n[bold cyan]{category.value}[/bold cyan] ({len(missing)} questions)")
        console.print()
        
        for i, question in enumerate(missing, 1):
            await self._ask_single_question(question, i, len(missing))
    
    async def _ask_single_question(self, question: DiscoveryQuestion, current: int, total: int):
        """Ask a single discovery question with validation and edit capability"""
        # Question header
        priority_color = {
            InformationPriority.CRITICAL: "red",
            InformationPriority.HIGH: "yellow",
            InformationPriority.MEDIUM: "cyan",
            InformationPriority.LOW: "white"
        }
        
        console.print(f"[{priority_color[question.priority]}]({current}/{total}) "
                     f"[{question.priority.value.upper()}][/{priority_color[question.priority]}]")
        console.print(f"[bold]{question.question}[/bold]")
        
        # Help text
        if question.help_text:
            console.print(f"[dim]{question.help_text}[/dim]")
        
        # Examples
        if question.examples:
            console.print("\n[dim]Examples:[/dim]")
            for example in question.examples[:3]:  # Show max 3 examples
                console.print(f"  [dim]• {example}[/dim]")
        
        # Check if we have a cached low-confidence answer
        cached = self.agent.answer_cache.get(question.id)
        if cached:
            console.print(f"\n[yellow]AI found a potential answer (confidence: {cached.confidence:.0%}):[/yellow]")
            console.print(f"[dim]\"{cached.answer}\"[/dim]")
            console.print(f"[dim]Source: {cached.document_reference}[/dim]")
            
            if Confirm.ask("Accept this answer?", default=True):
                # Accept cached answer
                self.agent.session.answers[question.id] = cached
                del self.agent.answer_cache[question.id]
                console.print("[green]✓[/green] Accepted\n")
                self.last_question = question
                return
            else:
                console.print("[yellow]Provide your own answer below:[/yellow]")
        
        # Get answer
        console.print()
        answer = Prompt.ask("Your answer (or 'skip' to skip, 'e' to edit last, '?' for help)", default="")
        
        # Handle interactive commands
        if answer.startswith('?'):
            if self.helper.process_command(answer):
                # Command was processed, re-ask the question
                await self._ask_single_question(question, current, total)
                return
        
        # Handle edit last answer
        if answer.lower() == 'e' and self.last_question:
            await self._edit_last_answer()
            # Re-ask current question
            await self._ask_single_question(question, current, total)
            return
        
        if answer and answer.strip() and answer.lower() != 'skip':
            # Record answer with validation
            _, validations = await self.agent.ask_user_question(question, answer.strip())
            
            # Display validation results
            if validations:
                self._display_validations(validations)
            
            # Track for editing
            self.last_question = question
            self.answers_this_session.append((question, answer.strip()))
            
            console.print("[green]✓[/green] Recorded\n")
        else:
            console.print("[yellow]⊘[/yellow] Skipped\n")
    
    def _display_validations(self, validations):
        """Display validation results to user"""
        for validation in validations:
            if validation.severity == ValidationSeverity.SUCCESS:
                console.print(f"[green]✓[/green] {validation.message}")
            elif validation.severity == ValidationSeverity.INFO:
                console.print(f"[blue]ℹ[/blue] {validation.message}")
                if validation.recommendation:
                    console.print(f"  [dim]{validation.recommendation}[/dim]")
            elif validation.severity == ValidationSeverity.WARNING:
                console.print(f"[yellow]⚠[/yellow] {validation.message}")
                if validation.recommendation:
                    console.print(f"  [dim]Recommendation: {validation.recommendation}[/dim]")
            elif validation.severity == ValidationSeverity.ERROR:
                console.print(f"[red]✗[/red] {validation.message}")
                if validation.recommendation:
                    console.print(f"  [dim]Fix: {validation.recommendation}[/dim]")
        console.print()
    
    async def _edit_last_answer(self):
        """Edit the last answer given"""
        if not self.last_question:
            console.print("[yellow]No previous answer to edit[/yellow]\n")
            return
        
        last_answer = self.agent.session.answers.get(self.last_question.id)
        if not last_answer:
            console.print("[yellow]Previous answer not found[/yellow]\n")
            return
        
        console.print("\n[cyan]--- Edit Last Answer ---[/cyan]")
        console.print(f"Question: {self.last_question.question}")
        console.print(f"Current answer: [yellow]{last_answer.answer}[/yellow]\n")
        
        new_answer = Prompt.ask("New answer", default=last_answer.answer)
        
        if new_answer != last_answer.answer:
            _, validations = await self.agent.ask_user_question(self.last_question, new_answer)
            console.print("[green]✓[/green] Answer updated\n")
            
            if validations:
                self._display_validations(validations)
        else:
            console.print("[dim]No changes made[/dim]\n")
    
    async def interactive_category_selection(self):
        """Step 3: Let user choose categories to complete"""
        console.print("\n[bold cyan]Step 3: Complete Additional Information[/bold cyan]")
        console.print("You can now fill in additional details by category.\n")
        
        categories = list(DiscoveryCategory)
        
        while True:
            # Show category menu
            table = Table(title="Discovery Categories", box=box.ROUNDED)
            table.add_column("#", style="cyan", width=3)
            table.add_column("Category", style="bold")
            table.add_column("Questions", justify="right")
            table.add_column("Status", justify="center")
            
            for i, category in enumerate(categories, 1):
                category_questions = get_questions_by_category(category)
                answered = sum(1 for q in category_questions if q.id in self.agent.session.answers)
                total = len(category_questions)
                
                status = "✓" if answered == total else f"{answered}/{total}"
                status_color = "green" if answered == total else "yellow"
                
                table.add_row(
                    str(i),
                    category.value,
                    str(total),
                    f"[{status_color}]{status}[/{status_color}]"
                )
            
            console.print(table)
            console.print("\n[dim]Options: Enter category number, 's' to skip, 'q' to finish[/dim]")
            
            choice = Prompt.ask("Select category", default="s")
            
            if choice.lower() == 'q':
                break
            elif choice.lower() == 's':
                if Confirm.ask("Skip remaining categories?", default=True):
                    break
                continue
            
            try:
                idx = int(choice) - 1
                if 0 <= idx < len(categories):
                    await self.ask_questions_by_category(categories[idx])
                else:
                    console.print("[red]Invalid category number[/red]\n")
            except ValueError:
                console.print("[red]Please enter a valid number[/red]\n")
    
    def show_final_summary(self):
        """Step 4: Show final discovery summary"""
        console.print("\n[bold green]Discovery Workshop Complete! 🎉[/bold green]\n")
        
        summary = self.agent.get_discovery_summary()
        
        # Summary panel
        summary_text = f"""
**Total Questions:** {summary['answered']}/{summary['total_questions']} ({summary['completion_percentage']:.1f}%)
**Documents Analyzed:** {summary['documents_analyzed']}
**Answers from Documents:** {summary['answers_from_documents']}
**Answers from You:** {summary['answers_from_user']}
**Critical Questions:** {summary['critical_questions']['answered']}/{summary['critical_questions']['total']} ({summary['critical_questions']['percentage']:.1f}%)
"""
        
        console.print(Panel(Markdown(summary_text), title="Discovery Summary", border_style="green"))
        
        # Missing critical info
        if summary['missing_critical']:
            console.print("\n[bold yellow]⚠ Missing Critical Information:[/bold yellow]")
            for question in summary['missing_critical'][:5]:  # Show first 5
                console.print(f"  • {question}")
            if len(summary['missing_critical']) > 5:
                console.print(f"  [dim]... and {len(summary['missing_critical']) - 5} more[/dim]")
            console.print()
    
    async def review_and_edit_answers(self):
        """Allow user to review and edit answers before export"""
        if not Confirm.ask("\nWould you like to review/edit your answers?", default=False):
            return
        
        console.print("\n[cyan]--- Answer Review ---[/cyan]\n")
        
        # Show all answers with edit option
        answers = list(self.agent.session.answers.items())
        
        for idx, (qid, answer) in enumerate(answers, 1):
            question = DISCOVERY_QUESTIONS[qid]
            
            console.print(f"\n[{idx}/{len(answers)}] [bold]{question.question}[/bold]")
            console.print(f"Answer: [cyan]{answer.answer}[/cyan]")
            console.print(f"Source: [dim]{answer.source}[/dim]")
            
            choice = Prompt.ask("[e]dit, [d]elete, [n]ext", default="n", choices=["e", "d", "n"])
            
            if choice == 'e':
                new_answer = Prompt.ask("New answer", default=answer.answer)
                if new_answer != answer.answer:
                    _, validations = await self.agent.ask_user_question(question, new_answer)
                    console.print("[green]✓[/green] Updated")
                    if validations:
                        self._display_validations(validations)
            elif choice == 'd':
                if Confirm.ask("Delete this answer?", default=False):
                    del self.agent.session.answers[qid]
                    console.print("[yellow]✓[/yellow] Deleted")
        
        console.print("\n[green]Review complete[/green]\n")
    
    def export_results(self):
        """Export discovery results"""
        output_file = f"discovery_results_{self.session_id}.json"
        self.agent.export_discovery_results(output_file)
        console.print(f"\n[green]✓[/green] Results exported to: [cyan]{output_file}[/cyan]")
        console.print("\n[dim]This file contains all gathered information and can be used for:[/dim]")
        console.print("[dim]  • Azure Landing Zone design[/dim]")
        console.print("[dim]  • Infrastructure-as-Code generation[/dim]")
        console.print("[dim]  • Stakeholder review and approval[/dim]\n")
    
    def show_cost_estimate(self):
        """Display cost estimation"""
        console.print("\n[bold cyan]Cost Estimation[/bold cyan]")
        console.print("[dim]Analyzing requirements to estimate Azure costs...[/dim]\n")
        
        estimate = self.agent.estimate_costs()
        
        if not estimate:
            console.print("[yellow]Insufficient data for cost estimation[/yellow]\n")
            return
        
        summary = estimate.get('summary', {})
        
        # Summary table
        table = Table(title="Estimated Azure Costs", box=box.ROUNDED)
        table.add_column("Category", style="cyan")
        table.add_column("Monthly", style="green", justify="right")
        table.add_column("Annual", style="green", justify="right")
        
        for category, data in estimate.get('breakdown', {}).items():
            table.add_row(
                category,
                f"${data['monthly']:,.2f}",
                f"${data['annual']:,.2f}"
            )
        
        # Totals
        table.add_row(
            "[bold]Total[/bold]",
            f"[bold]${summary['monthly_cost']:,.2f}[/bold]",
            f"[bold]${summary['annual_cost']:,.2f}[/bold]",
            style="bold"
        )
        
        if summary.get('potential_savings', 0) > 0:
            table.add_row(
                "[green]Potential Savings[/green]",
                "",
                f"[green]-${summary['potential_savings']:,.2f}[/green]"
            )
            table.add_row(
                "[bold]Net Annual Cost[/bold]",
                "",
                f"[bold]${summary['net_annual_cost']:,.2f}[/bold]",
                style="bold green"
            )
        
        console.print(table)
        console.print(f"\n[dim]Region: {summary['region']} | Currency: {summary['currency']}[/dim]")
        console.print("[dim]Note: Estimates are approximate and based on assumptions.[/dim]\n")
    
    def show_architecture_preview(self):
        """Display architecture diagram preview"""
        console.print("\n[bold cyan]Architecture Preview[/bold cyan]")
        console.print("[dim]Generating Landing Zone architecture based on your answers...[/dim]\n")
        
        try:
            # Get current discovery results
            results = {
                "session": {
                    "id": self.agent.session.session_id,
                    "timestamp": self.agent.session.timestamp.isoformat(),
                    "completion": self.agent.session.completion_percentage
                },
                "summary": self.agent.get_discovery_summary(),
                "answers": [
                    {
                        "question_id": qid,
                        "question": DISCOVERY_QUESTIONS[qid].question,
                        "category": DISCOVERY_QUESTIONS[qid].category.value,
                        "priority": DISCOVERY_QUESTIONS[qid].priority.value,
                        "answer": answer.answer,
                        "source": answer.source,
                        "confidence": answer.confidence,
                        "document_reference": answer.document_reference
                    }
                    for qid, answer in self.agent.session.answers.items()
                ]
            }
            
            visualizer = ArchitectureVisualizer(results)
            ascii_diagram = visualizer.generate_ascii_diagram()
            
            console.print("[green]" + ascii_diagram + "[/green]")
            
            # Offer to save diagrams
            if Confirm.ask("\nSave architecture diagrams (HTML, Mermaid)?", default=False):
                outputs = visualizer.save_all_formats()
                console.print("\n[green]Architecture diagrams saved:[/green]")
                for format_type, path in outputs.items():
                    console.print(f"  • {format_type.upper()}: [cyan]{path}[/cyan]")
                console.print()
        except Exception as e:
            console.print(f"[yellow]⚠ Could not generate architecture preview: {str(e)}[/yellow]\n")
    
    async def run_workshop(self):
        """Run the complete discovery workshop"""
        try:
            # Welcome
            self.show_welcome()
            self.show_configuration()
            
            if not Confirm.ask("Proceed with this configuration?", default=True):
                console.print("[yellow]Workshop cancelled[/yellow]")
                return
            
            # Start session (automatically loads previous answers)
            await self.agent.start_discovery_workshop(self.session_id, auto_resume=True)
            
            if self.agent.session.get_answered_count() > 0:
                console.print(f"\n[green]✓[/green] Auto-loaded [cyan]{self.agent.session.get_answered_count()}[/cyan] answers from previous session")
                console.print(f"[green]✓[/green] Session ID: [cyan]{self.agent.session.session_id}[/cyan]\n")
            else:
                console.print(f"\n[green]✓[/green] Started new discovery session: [cyan]{self.session_id}[/cyan]\n")
            
            # Step 1: Analyze documents (skip if we already have answers loaded)
            if self.agent.session.get_answered_count() == 0:
                await self.analyze_documents_step()
            else:
                console.print("\n[dim]Skipping document analysis (answers loaded from previous session)[/dim]\n")
            
            # Show progress
            self.show_discovery_progress()
            
            # Step 2: Critical questions
            await self.ask_critical_questions()
            
            # Show updated progress
            self.show_discovery_progress()
            
            # Step 3: Optional category completion
            if Confirm.ask("Would you like to complete additional categories?", default=True):
                await self.interactive_category_selection()
            
            # Step 4: Final summary
            self.show_final_summary()
            
            # Cost estimation
            if Confirm.ask("\nWould you like to see cost estimates?", default=True):
                self.show_cost_estimate()
            
            # Architecture preview
            if Confirm.ask("\nWould you like to see the Landing Zone architecture?", default=True):
                self.show_architecture_preview()
            
            # Review and edit
            await self.review_and_edit_answers()
            
            # Export results
            if Confirm.ask("Export discovery results?", default=True):
                self.export_results()
                
                # Offer enhanced exports
                if Confirm.ask("\nGenerate professional reports (PDF/Word/Excel)?", default=False):
                    await self.export_enhanced_reports()
            
            console.print("\n[bold green]Thank you for completing the discovery workshop![/bold green] 🙏\n")
            
        except KeyboardInterrupt:
            console.print("\n\n[yellow]Workshop interrupted by user[/yellow]")
        except Exception as e:
            console.print(f"\n[red]Error during workshop: {str(e).replace('[', '').replace(']', '')}[/red]")
            logging.exception("Workshop error")
    
    async def export_enhanced_reports(self):
        """Export enhanced reports in multiple formats"""
        console.print("\n[cyan]Generating professional reports...[/cyan]\n")
        
        formats = []
        if Confirm.ask("Generate PDF report?", default=True):
            formats.append(('pdf', f"report_{self.session_id}.pdf"))
        if Confirm.ask("Generate Word document?", default=False):
            formats.append(('docx', f"report_{self.session_id}.docx"))
        if Confirm.ask("Generate Excel spreadsheet?", default=False):
            formats.append(('xlsx', f"report_{self.session_id}.xlsx"))
        
        for format_type, filename in formats:
            try:
                output = self.agent.export_enhanced_report(filename, format_type)
                console.print(f"[green]✓[/green] {format_type.upper()} report: [cyan]{output}[/cyan]")
            except Exception as e:
                console.print(f"[yellow]⚠[/yellow] Could not generate {format_type.upper()}: {str(e)}")
        
        console.print()


async def main():
    """Entry point for discovery workshop"""
    # Set logging level
    logging.basicConfig(level=logging.WARNING)
    
    cli = DiscoveryWorkshopCLI()
    await cli.run_workshop()


if __name__ == "__main__":
    asyncio.run(main())
