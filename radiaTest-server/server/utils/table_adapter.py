from server.model import (
    Product,
    Milestone,
    Pmachine,
    Vmachine,
    MachineGroup,
    Template,
    IMirroring,
    QMirroring,
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
