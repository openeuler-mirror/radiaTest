from server.model import (
    Product,
    Milestone,
    Pmachine,
    Vmachine,
    MachineGroup,
    IMirroring,
    QMirroring,
)

class TableAdapter:
    product=Product
    milestone=Milestone
    pmachine=Pmachine
    vmachine=Vmachine
    machine_group=MachineGroup
    i_mirroring=IMirroring
    q_mirroring=QMirroring
