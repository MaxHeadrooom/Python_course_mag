from .analyzers import AnalysisContext
from .errors import AnalysisFailure
from .models import AnalysisReport
from .registry import AnalyzerRegistry
from .repository import SubmissionRepository


class AnalysisService:
    def __init__(self, repository: SubmissionRepository, registry: AnalyzerRegistry) -> None:
        self.repository = repository
        self.registry = registry

    def run(self, submission_id: str, analyzer_name: str, context: AnalysisContext) -> AnalysisReport:
        submission = self.repository.get(submission_id)

        if submission is None:
            raise AnalysisFailure("No such submission")

        if submission.assignment_id != context.assignment.assignment_id:
            raise AnalysisFailure("Must be same context")

        analyzer = self.registry.create(analyzer_name)

        report = analyzer.analyze(submission, context)

        if report.analyzer_id != analyzer.analyzer_id or analyzer.analyzer_version != report.analyzer_version:
            raise AnalysisFailure("Analysis id doesn't match submission")

        return report
