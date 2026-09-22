"""New fix's

Revision ID: 05b87d09b055
Revises: b530c49f6748
Create Date: 2026-09-21 12:54:13.180983

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel


# revision identifiers, used by Alembic.
revision: str = '05b87d09b055'
down_revision: Union[str, None] = 'b530c49f6748'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
