# coding=UTF-8
from ondestan.entities import Plot
from sqlalchemy import and_

import logging

logger = logging.getLogger('ondestan')


def get_plot_by_id(plot_id):
    if plot_id != None:
        return Plot().queryObject().filter(Plot.id == plot_id).scalar()
    else:
        return None


def get_all_plots(email=None):
    if email != None:
        return Plot().queryObject().filter(Plot.user.has(email=email)).\
            order_by(Plot.name, Plot.id).all()
    else:
        return Plot().queryObject().order_by(Plot.name, Plot.id).all()


def update_plot_name(plot_id, name, user_id=None):
    if (id != None and name != None):
        if user_id != None:
            plot = Plot().queryObject().filter(and_(Plot.id == plot_id,
                    Plot.user_id == user_id)).scalar()
        else:
            plot = Plot().queryObject().filter(Plot.id ==
                    plot_id).scalar()
        if plot != None:
            plot.name = name
            plot.update()
        else:
            logger.error("Cannot update the non-existent plot with id "
                     + str(plot_id) + " for user id " + str(user_id))


def create_plot(points, name, user_id):
    if len(points) < 3:
        logger.error('A plot with less than 3 points cannot be saved...')
        return None
    geom_coordinates = ''
    for point in points:
        geom_coordinates += str(point[0]) + ' ' + str(point[1]) + ','
    geom_coordinates += str(points[0][0]) + ' ' + str(points[0][1])

    plot = Plot()
    plot.user_id = user_id
    plot.geom = 'SRID=' + str(plot.srid) + ';POLYGON((' + geom_coordinates\
        + '))'
    plot.name = name
    plot.save()

    return plot


def update_plot_geom(points, plot_id, user_id=None):
    if len(points) < 3:
        logger.error('A plot with less than 3 points cannot be saved...')
        return None
    geom_coordinates = ''
    for point in points:
        geom_coordinates += str(point[0]) + ' ' + str(point[1]) + ','
    geom_coordinates += str(points[0][0]) + ' ' + str(points[0][1])

    if user_id != None:
        plot = Plot().queryObject().filter(and_(Plot.id == plot_id, Plot.user_id
                                            == user_id)).scalar()
    else:
        plot = Plot().queryObject().filter(Plot.id == plot_id).scalar()
    if plot == None:
        logger.error("Cannot update the non-existent plot with id "
                     + str(plot_id) + " for user id " + str(user_id))
        return None
    plot.geom = 'SRID=' + str(plot.srid) + ';POLYGON((' + geom_coordinates\
        + '))'
    plot.update()

    return plot


def delete_plot(plot_id, user_id=None):
    if user_id != None:
        plot = Plot().queryObject().filter(and_(Plot.id == plot_id, Plot.user_id
                                            == user_id)).scalar()
    else:
        plot = Plot().queryObject().filter(Plot.id == plot_id).scalar()
    if plot == None:
        logger.error("Cannot delete the non-existent plot with id "
                     + str(plot_id) + " for user id " + str(user_id))
        return False
    plot.delete()

    return True
