# coding=UTF-8
from sqlalchemy import Column, Integer, ForeignKey, String, Boolean
from sqlalchemy.orm import relationship, backref
from sqlalchemy.ext.hybrid import hybrid_property

from ondestan.entities import Entity
from ondestan.entities.position import Position
from ondestan.utils import Base


class Animal(Entity, Base):

    __tablename__ = "animals"

    id = Column(Integer, primary_key=True)
    name = Column(String)
    type = Column(String)
    imei = Column(String)
    phone = Column(String)
    active = Column(Boolean)
    user_id = Column(Integer, ForeignKey("users.id"))
    user = relationship("User", backref=backref('animals',
                                                  order_by=name))
    order_id = Column(Integer, ForeignKey("orders.id"))
    order = relationship("Order", backref=backref('animals',
                                                  order_by=name))
    """plot_id = Column(Integer, ForeignKey("plots.id"))
    plot = relationship("Plot", backref=backref('animals',
                                                  order_by=name))"""

    @hybrid_property
    def n_positions(self):
        if self.id != None:
            return Position().queryObject().filter(Position.animal_id
                    == self.id).count()
        return 0

    @hybrid_property
    def positions(self):
        if self.id != None:
            return Position().queryObject().filter(Position.animal_id
                    == self.id).order_by(Position.date.desc()).yield_per(100)
        return []

    @hybrid_property
    def currently_outside(self):
        if self.n_positions > 0:
            return self.positions[0].outside()
        return None
