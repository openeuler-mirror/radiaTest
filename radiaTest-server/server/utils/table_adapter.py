from server.model import (
    Product,
    Milestone,
    Pmachine,
    Vmachine,
    MachineGroup,
    Template,
    IMirroring,
    QMirroring,
    Framework,
    GitRepo,
    SuiteDocument,
    BaselineTemplate,
    BaseNode,
)

class TableAdapter:
    product=Product
    milestone=Milestone
    pmachine=Pmachine
    vmachine=Vmachine
    machine_group=MachineGroup
    template=Template
    i_mirroring=IMirroring
    q_mirroring=QMirroring
    framework=Framework
    git_repo=GitRepo
    suite_document=SuiteDocument
    baseline_template=BaselineTemplate
    base_node=BaseNode