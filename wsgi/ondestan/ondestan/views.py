# coding=UTF-8
from pyramid.httpexceptions import (
    HTTPFound
    )

from pyramid.view import (
    view_config,
    forbidden_view_config
    )

from pyramid.security import (
    remember,
    forget
    )

from pyramid.i18n import (
    get_localizer,
    TranslationString as _
    )
from webhelpers.paginate import Page

from ondestan.security import get_user_email, check_permission
from ondestan.services import plot_service, animal_service, user_service
from ondestan.services import order_service, notification_service
from ondestan.gps import comms_service
from ondestan.gps.gps_update_error import GpsUpdateError
from ondestan.utils import Customizable_PageURL_WebOb, format_utcdatetime, parse_to_utcdatetime
from ondestan.utils import get_device_config_fancy_description, get_fancy_time_from_utc, get_device_preconfig_names
from ondestan.config import Config

max_positions = Config.get_int_value('config.history_max_positions')

import logging, json, urllib2
from datetime import datetime

logger = logging.getLogger('ondestan')
logger_nominatim = logging.getLogger('nominatim')


@view_config(route_name='login', renderer='templates/login.pt')
@forbidden_view_config(renderer='templates/login.pt')
def login(request):
    activated = False
    if 'activated' in request.params:
        activated = request.params['activated'].lower() == 'true'
    referrer = request.url
    base_referrer = referrer[0:referrer.find('?')] if referrer.find('?') != -1\
        else referrer
    if base_referrer == request.route_url('login'):
        # never use the login form itself as came_from
        # use main view instead
        referrer = 'map'
    came_from = request.params.get('came_from', referrer)
    message = ''
    email = ''
    if 'form.submitted' in request.params:
        email = request.params['email']
        if user_service.check_login_request(request):
            headers = remember(request, email)
            return HTTPFound(location=came_from,
                             headers=headers)

        localizer = get_localizer(request)
        message_ts = _('failed_login', domain='Ondestan')
        message = localizer.translate(message_ts)

    return dict(
        message=message,
        came_from=came_from,
        email=email,
        activated=activated
        )


@view_config(route_name='tour', renderer='templates/tour.pt')
def tour(request):
    return dict()


@view_config(route_name='gps_update')
def gps_update(request):
    return comms_service.process_update_request(request)


@view_config(route_name='signup', renderer='templates/signup.pt')
def signup(request):
    message = ''
    name = ''
    email = ''
    phone = ''
    if 'form.submitted' in request.params:
        message = user_service.create_user(request)
        if message != '':
            name = request.params['name']
            email = request.params['email']
            phone = request.params['phone']

    return dict(
        message=message,
        name=name,
        email=email,
        phone=phone,
        )


@view_config(route_name='update_animal_name', permission='view')
def update_animal_name(request):
    if 'name' in request.params and 'id' in request.params:
        if check_permission('admin', request):
            animal_service.update_animal_name(request.params['id'],
                                          request.params['name'])
        else:
            user = user_service.get_user_by_email(get_user_email(request))
            animal_service.update_animal_name(request.params['id'],
                                          request.params['name'], user.id)
    return HTTPFound(location=request.route_url('map'))


@view_config(route_name='update_profile',
             renderer='templates/updateProfile.pt',
             permission='view')
def update_profile(request):
    notifications = []

    if 'form.submitted' in request.params:
        if 'email' in request.params:
            notifications.append(user_service.update_user(request))
            name = request.params['name']
            email = request.params['email']
            phone = request.params['phone']
            user_id = request.params['id']
            headers = remember(request, email)
            request.response.headerlist.extend(headers)

        else:
            if 'password' in request.params:
                notifications.append(user_service.update_password(request))
            user = user_service.get_user_by_email(get_user_email(request))
            user_id = user.id
            name = user.name
            email = user.email
            phone = user.phone
    else:
        user = user_service.get_user_by_email(get_user_email(request))
        user_id = user.id
        name = user.name
        email = user.email
        phone = user.phone

    return dict(
        notifications=notifications,
        id=user_id,
        name=name,
        email=email,
        phone=phone
        )


@view_config(route_name='password_reset',
             renderer='templates/passwordReset.pt')
def password_reset(request):
    email = ''
    if 'form.submitted' in request.params:
        user_service.reset_password(request)
        email = request.params['email']

    return dict(
        email=email,
        )


@view_config(route_name='activate_user')
def activate_usr(request):
    user_service.activate_user(request)
    return HTTPFound(location=request.route_url('login') + '?activated=true')


@view_config(route_name='logout')
def logout(request):
    headers = forget(request)
    return HTTPFound(location=request.route_url('login'),
                     headers=headers)


@view_config(route_name='check_device_phone', renderer='json',
             permission='admin')
def check_device_phone(request):
    if 'phone' in request.params:
        phone = request.params['phone']
        animal = animal_service.get_animal_by_phone(phone)
        if (animal == None):
            return True
        if 'id' in request.params:
            if animal.id == int(request.params['id']):
                return True
    localizer = get_localizer(request)
    message_ts = _('device_phone_already_use', domain='Ondestan')
    return localizer.translate(message_ts)


@view_config(route_name='check_device_imei', renderer='json',
             permission='admin')
def check_device_imei(request):
    if 'imei' in request.params:
        imei = request.params['imei']
        animal = animal_service.get_animal_by_imei(imei)
        if (animal == None):
            return True
        if 'id' in request.params:
            if animal.id == int(request.params['id']):
                return True
    localizer = get_localizer(request)
    message_ts = _('device_imei_already_use', domain='Ondestan')
    return localizer.translate(message_ts)


@view_config(route_name='check_user_email', renderer='json')
def check_user_email(request):
    if 'email' in request.params:
        email = request.params['email']
        user = user_service.get_user_by_email(email)
        if (user == None):
            return True
        if 'id' in request.params:
            if user.id == int(request.params['id']):
                return True
    localizer = get_localizer(request)
    message_ts = _('user_email_already_use', domain='Ondestan')
    return localizer.translate(message_ts)


@view_config(route_name='orders', renderer='templates/orders.pt',
             permission='view')
def orders(request):
    message = ''
    units = ''
    address = ''
    if 'form.submitted' in request.params:
        if 'id' in request.params:
            order_id = int(request.params['id'])
            state = int(request.params['state'])

            message = order_service.update_order_state(order_id, state,
                                                       request)
        else:
            message = order_service.create_order(request)
            if message != '':
                units = request.params['units']
                address = request.params['address']

    is_admin = check_permission('admin', request)
    if is_admin:
        query1 = order_service.get_all_pending_orders()
        pending_orders = Page(query1,
            page=int(request.params.get('p1', 1)),
            items_per_page=10,
            url=Customizable_PageURL_WebOb(request, get_param='p1'))
        query2 = order_service.get_all_processed_orders()
        processed_orders = Page(query2,
            page=int(request.params.get('p2', 1)),
            items_per_page=10,
            url=Customizable_PageURL_WebOb(request, get_param='p2'))
    else:
        query1 = order_service.get_all_pending_orders(
            get_user_email(request))
        pending_orders = Page(query1,
            page=int(request.params.get('p1', 1)),
            items_per_page=10,
            url=Customizable_PageURL_WebOb(request, get_param='p1'))
        query2 = order_service.get_all_processed_orders(
            get_user_email(request))
        processed_orders = Page(query2,
            page=int(request.params.get('p2', 1)),
            items_per_page=10,
            url=Customizable_PageURL_WebOb(request, get_param='p2'))

    is_admin = check_permission('admin', request)

    return dict(
        message=message,
        units=units,
        address=address,
        pending_orders=pending_orders,
        processed_orders=processed_orders,
        is_admin=is_admin
        )


@view_config(route_name='order_state_history',
             renderer='templates/orderStateHistory.pt',
             permission='admin')
def order_state_history(request):
    order = order_service.get_order_by_id(
                request.matchdict['order_id'])
    if (order == None):
        return HTTPFound(request.route_url("orders"))
    states = Page(order.states,
            page=int(request.params.get('p', 1)),
            items_per_page=20,
            url=Customizable_PageURL_WebOb(request, get_param='p'))
    return dict(
        states=states
        )


@view_config(route_name='order_devices',
             renderer='templates/orderDevices.pt',
             permission='admin')
def order_devices(request):
    order = order_service.get_order_by_id(
                request.matchdict['order_id'])
    if (order == None):
        return HTTPFound(request.route_url("orders"))
    if 'form.submitted' in request.params:
        if 'imei' in request.params and 'phone' in request.params:
            imei = request.params['imei']
            phone = request.params['phone']
            name = request.params['name']

            animal_service.create_animal(imei, phone, order, name)

    return dict(
        order=order,
        )


@view_config(route_name='notifications',
             renderer='templates/notifications.pt',
             permission='view')
def notifications(request):
    query = notification_service.get_all_notifications(request)
    notifications = Page(query,
        page=int(request.params.get('p', 1)),
        items_per_page=20,
        url=Customizable_PageURL_WebOb(request, get_param='p'))
    return dict(
        is_admin=check_permission('admin', request),
        notifications=notifications
        )


@view_config(route_name='delete_device',
             permission='admin')
def delete_device(request):
    order_id = animal_service.get_animal_by_id(request.matchdict['device_id'])\
               .order_id
    animal_service.delete_animal_by_id(
                request.matchdict['device_id'])
    return HTTPFound(request.route_url("order_devices", order_id=order_id))


@view_config(route_name='activate_device',
             permission='view')
def activate_device(request):
    animal_service.activate_animal_by_id(request)
    return HTTPFound(request.route_url("map"))


@view_config(route_name='deactivate_device',
             permission='view')
def deactivate_device(request):
    animal_service.deactivate_animal_by_id(request)
    return HTTPFound(request.route_url("map"))


@view_config(route_name='map', renderer='templates/animalViewer.pt',
             permission='view')
def animal_viewer(request):
    user = user_service.get_user_by_email(get_user_email(request))
    view = user.get_animals_bounding_box_as_json()
    return dict(
        view=view if view != None else user.get_plots_bounding_box_as_json(),
        notifications=notification_service.\
            get_new_web_notifications_for_logged_user(request)
    )


@view_config(route_name='history_map',
             renderer='templates/animalHistoryViewer.pt',
             permission='view')
def animal_history_viewer(request):
    animal_id = request.matchdict['animal_id']
    email = get_user_email(request)
    is_admin = check_permission('admin', request)
    animal = None
    if animal_id != None:
        try:
            animal = animal_service.get_animal_by_id(int(animal_id))
        except ValueError:
            pass
    if (animal == None) or (not is_admin and animal.user.email != email):
        return HTTPFound(request.route_url("map"))
    parameters = {
        'max_positions': max_positions
    }
    too_many_positions_msg = _("too_many_positions_in_selected_time_interval",
                               domain='Ondestan',
                               mapping=parameters)
    return dict(
        view=animal.get_bounding_box_as_json(),
        animal_id=animal_id,
        too_many_positions_msg=get_localizer(request).\
            translate(too_many_positions_msg)
    )


@view_config(route_name='charging_history_map',
             renderer='templates/animalChargingHistoryViewer.pt',
             permission='admin')
def animal_charging_history_viewer(request):
    animal_id = request.matchdict['animal_id']
    email = get_user_email(request)
    is_admin = check_permission('admin', request)
    animal = None
    if animal_id != None:
        try:
            animal = animal_service.get_animal_by_id(int(animal_id))
        except ValueError:
            pass
    if (animal == None) or (not is_admin and animal.user.email != email):
        return HTTPFound(request.route_url("map"))
    parameters = {
        'max_positions': max_positions
    }
    too_many_positions_msg = _("too_many_positions_in_selected_time_interval",
                               domain='Ondestan',
                               mapping=parameters)
    return dict(
        view=animal.get_bounding_box_as_json(),
        animal_id=animal_id,
        too_many_positions_msg=get_localizer(request).\
            translate(too_many_positions_msg)
    )


@view_config(route_name='plot_manager', renderer='templates/plotManager.pt',
             permission='view')
def plot_manager(request):
    user = user_service.get_user_by_email(get_user_email(request))
    is_admin = check_permission('admin', request)
    return dict(
        is_admin=is_admin,
        non_admin_users=user_service.get_non_admin_users() if is_admin else [],
        view=user.get_plots_bounding_box_as_json()
    )


@view_config(route_name='default')
def default(request):
    return HTTPFound(request.route_url("map"))


@view_config(route_name='update_plot_name', permission='view')
def update_plot_name(request):
    if 'name' in request.params and 'id' in request.params:
        if check_permission('admin', request):
            plot_service.update_plot_name(request.params['id'],
                                          request.params['name'])
        else:
            user = user_service.get_user_by_email(get_user_email(request))
            plot_service.update_plot_name(request.params['id'],
                                          request.params['name'], user.id)
    return HTTPFound(location=request.route_url('plot_manager'))


@view_config(route_name='create_plot', renderer='json',
             permission='view')
def create_plot(request):
    points = []
    i = 0
    while ('x' + str(i)) in request.GET and ('y' + str(i)) in request.GET:
        points.append([float(request.GET['x' + str(i)]), float(request.GET['y'
                                                                + str(i)])])
        i += 1

    if 'name' in request.GET:
        name = request.GET['name']
    else:
        name = ''
    if 'userid' in request.GET and check_permission('admin', request):
        userid = request.GET['userid']
    else:
        userid = user_service.get_user_by_email(get_user_email(request)).id

    plot = plot_service.create_plot(points, name, userid)

    if plot == None:
        return {'success': False}
    else:
        feature = {
                    "type": "Feature",
                    "properties": {
                        "id": plot.id,
                        "name": plot.name,
                        "owner": plot.user.email,
                        "popup": plot.name
                    },
                    "geometry": eval(plot.geojson)
                }
        return {'success': True, 'feature': feature}


@view_config(route_name='update_plot_geom', renderer='json',
             permission='view')
def update_plot_geom(request):
    points = []
    i = 0
    while ('x' + str(i)) in request.GET and ('y' + str(i)) in request.GET:
        points.append([float(request.GET['x' + str(i)]), float(request.GET['y'
                                                                + str(i)])])
        i += 1
    plot_id = request.GET['id']
    if check_permission('admin', request):
        plot = plot_service.update_plot_geom(points, plot_id)
    else:
        user = user_service.get_user_by_email(get_user_email(request))
        plot = plot_service.update_plot_geom(points, plot_id, user.id)

    if plot == None:
        return {'success': False}
    else:
        feature = {
                    "type": "Feature",
                    "properties": {
                        "id": plot_id,
                        "name": plot.name,
                        "owner": plot.user.email,
                        "popup": plot.name
                    },
                    "geometry": eval(plot.geojson)
                }
        return {'success': True, 'feature': feature}


@view_config(route_name='delete_plot', renderer='json',
             permission='view')
def delete_plot(request):
    plot_id = request.GET['id']
    if check_permission('admin', request):
        return {'success': plot_service.delete_plot(plot_id)}
    else:
        user = user_service.get_user_by_email(get_user_email(request))
        return {'success': plot_service.delete_plot(plot_id, user.id)}


@view_config(route_name='json_animal_approx_position', renderer='json',
             permission='view')
def json_animal_approx_position(request):
    geojson = []
    animal_id = request.matchdict['animal_id']
    is_admin = check_permission('admin', request)
    email = get_user_email(request)
    animal = None
    if animal_id != None:
        try:
            animal = animal_service.get_animal_by_id(int(animal_id))
        except ValueError:
            pass
    if animal != None and (is_admin or animal.user.email == email):
        instant = datetime.utcnow()
        position = animal.get_approx_position_as_geojson(instant)
        if position != None:
            parameters = {
                'animal_name': animal.name,
                'name': animal.user.email,
                'imei': animal.imei,
                'date': format_utcdatetime(instant,
                                           request)
            }
            if is_admin:
                popup_str = _("animal_app_position_popup_admin", domain='Ondestan',
                              mapping=parameters)
            else:
                popup_str = _("animal_app_position_popup", domain='Ondestan',
                              mapping=parameters)
            geojson.append({
                "type": "Feature",
                "properties": {
                    "id": animal.id,
                    "name": animal.name,
                    "imei": animal.imei,
                    "owner": animal.user.email,
                    "active": animal.active,
                    "date": format_utcdatetime(instant,
                                           request),
                    "popup": get_localizer(request).translate(
                                                        popup_str)
                },
                "geometry": eval(position)
            })
    return geojson


@view_config(route_name='json_animals', renderer='json',
             permission='view')
def json_animals(request):
    geojson = []
    if (check_permission('admin', request)):
        animals = animal_service.get_all_animals()
        if animals != None:
            logger.debug("Found " + str(len(animals)) +
                         " animals for all users")
            for animal in animals:
                if animal.n_positions > 0:
                    if animal.name != None and len(animal.name) > 0:
                        name = animal.name
                    else:
                        name = animal.imei
                    fancy_date = get_fancy_time_from_utc(animal.positions[0].\
                                                        date, request=request)
                    parameters = {
                        'animal_name': name,
                        'name': animal.user.email,
                        'imei': animal.imei,
                        'battery': str(animal.current_battery_wo_charging),
                        'date': fancy_date,
                        'plot': animal.plot.name if animal.plot != None\
                                else '---'
                    }
                    popup_str = _("animal_popup_admin", domain='Ondestan',
                                  mapping=parameters)
                    geojson.append({
                        "type": "Feature",
                        "properties": {
                            "id": animal.id,
                            "name": animal.name,
                            "imei": animal.imei,
                            "battery": animal.current_battery,
                            "battery_wo_charging": animal.current_battery_wo_charging,
                            "charging": animal.currently_charging,
                            "owner": animal.user.email,
                            "active": animal.active,
                            "last_date": format_utcdatetime(animal.\
                                                            positions[0].date,
                                                            request),
                            "fancy_last_date": fancy_date,
                            "outside": animal.positions[0].outside(),
                            "popup": get_localizer(request).translate(
                                                                popup_str)
                        },
                        "geometry": eval(animal.positions[0].geojson)
                    })
                else:
                    geojson.append({
                        "type": "Feature",
                        "properties": {
                            "id": animal.id,
                            "name": animal.name,
                            "imei": animal.imei,
                            "battery": None,
                            "battery_wo_charging": None,
                            "charging": None,
                            "owner": animal.user.email,
                            "active": animal.active,
                            "last_date": None,
                            "fancy_last_date": None,
                            "outside": None,
                            "popup": None
                        },
                        "geometry": None
                    })
        else:
            logger.debug("Found no animals for any user")
    else:
        email = get_user_email(request)
        animals = animal_service.get_all_animals(email)
        if animals != None:
            logger.debug("Found " + str(len(animals)) +
                         " animals for user " + email)
            for animal in animals:
                if animal.n_positions > 0:
                    if animal.name != None and len(animal.name) > 0:
                        name = animal.name
                    else:
                        name = animal.imei
                    fancy_date = get_fancy_time_from_utc(animal.positions[0].\
                                                        date, request=request)
                    parameters = {
                        'animal_name': name,
                        'name': animal.user.email,
                        'imei': animal.imei,
                        'battery': str(animal.current_battery_wo_charging),
                        'date': fancy_date,
                        'plot': animal.plot.name if animal.plot != None\
                                else '---'
                    }
                    popup_str = _("animal_popup", domain='Ondestan',
                                  mapping=parameters)
                    geojson.append({
                        "type": "Feature",
                        "properties": {
                            "id": animal.id,
                            "name": animal.name,
                            "imei": animal.imei,
                            "battery": animal.current_battery,
                            "battery_wo_charging": animal.current_battery_wo_charging,
                            "charging": animal.currently_charging,
                            "owner": animal.user.email,
                            "active": animal.active,
                            "last_date": format_utcdatetime(animal.\
                                                            positions[0].date,
                                                            request),
                            "fancy_last_date": fancy_date,
                            "outside": animal.positions[0].outside(),
                            "popup": get_localizer(request).translate(
                                                                popup_str)
                        },
                        "geometry": eval(animal.positions[0].geojson)
                    })
                else:
                    geojson.append({
                        "type": "Feature",
                        "properties": {
                            "id": animal.id,
                            "name": animal.name,
                            "imei": animal.imei,
                            "battery": None,
                            "battery_wo_charging": None,
                            "charging": None,
                            "owner": animal.user.email,
                            "active": animal.active,
                            "last_date": None,
                            "fancy_last_date": None,
                            "outside": None,
                            "popup": None
                        },
                        "geometry": None
                    })
        else:
            logger.debug("Found no animals for user " + email)
    return geojson


@view_config(route_name='json_animal_positions', renderer='json',
             permission='view')
def json_animal_positions(request):
    animal_id = request.matchdict['animal_id']
    email = get_user_email(request)
    is_admin = check_permission('admin', request)
    animal = None
    if animal_id != None:
        try:
            animal = animal_service.get_animal_by_id(int(animal_id))
        except ValueError:
            pass
    geojson = []
    if animal != None and (is_admin or animal.user.email == email):
        start = None
        end = None
        if 'start' in request.GET:
            try:
                start = parse_to_utcdatetime(request.GET['start'])
            except ValueError:
                pass
        if 'end' in request.GET:
            try:
                end = parse_to_utcdatetime(request.GET['end'])
            except ValueError:
                pass

        n_positions = animal.n_filter_positions(start, end)
        logger.debug("Found " + str(n_positions) +
                     " positions for animal " + str(animal_id))
        if n_positions > 0:
            if animal.name != None and len(animal.name) > 0:
                name = animal.name
            else:
                name = animal.imei
            positions = animal.filter_positions(start, end)
            for position in positions:
                if int(position.battery) == position.battery:
                    position.battery = int(position.battery)
                fancy_date = get_fancy_time_from_utc(position.\
                                                    date, request=request)
                parameters = {
                    'animal_name': name,
                    'name': animal.user.email,
                    'imei': animal.imei,
                    'battery': str(position.battery),
                    'date': fancy_date,
                    'plot': animal.plot.name if animal.plot != None else '---'
                }
                if is_admin:
                    popup_str = _("animal_popup_admin", domain='Ondestan',
                                  mapping=parameters)
                else:
                    popup_str = _("animal_popup", domain='Ondestan',
                                  mapping=parameters)
                geojson.append({
                    "type": "Feature",
                    "properties": {
                        "id": animal.id,
                        "name": animal.name,
                        "imei": animal.imei,
                        "battery": position.battery,
                        "owner": animal.user.email,
                        "active": animal.active,
                        "outside": position.outside(),
                        "date": format_utcdatetime(position.date,
                                               request),
                        "fancy_date": fancy_date,
                        "popup": get_localizer(request).translate(
                                                            popup_str)
                    },
                    "geometry": eval(position.geojson)
                })
                # We return the max number of positions plus one, so it can
                # detect there are more and not just the barrier number
                if len(geojson) == (max_positions + 1):
                    logger.warning("Too many positions requested for animal "
                        + str(animal_id) + ", only the last "
                        + str(max_positions + 1) + " will be returned")
                    break
        else:
            geojson.append({
                "type": "Feature",
                "properties": {
                    "id": animal.id,
                    "name": animal.name,
                    "imei": animal.imei,
                    "battery": None,
                    "owner": animal.user.email,
                    "active": animal.active,
                    "outside": None,
                    "date": None,
                    "fancy_date": None,
                    "popup": None
                },
                "geometry": None
            })
    return geojson


@view_config(route_name='json_animal_charging_positions', renderer='json',
             permission='admin')
def json_animal_charging_positions(request):
    animal_id = request.matchdict['animal_id']
    email = get_user_email(request)
    is_admin = check_permission('admin', request)
    animal = None
    if animal_id != None:
        try:
            animal = animal_service.get_animal_by_id(int(animal_id))
        except ValueError:
            pass
    geojson = []
    if animal != None and (is_admin or animal.user.email == email):
        start = None
        end = None
        if 'start' in request.GET:
            try:
                start = parse_to_utcdatetime(request.GET['start'])
            except ValueError:
                pass
        if 'end' in request.GET:
            try:
                end = parse_to_utcdatetime(request.GET['end'])
            except ValueError:
                pass

        n_positions = animal.n_filter_charging_positions(start, end)
        logger.debug("Found " + str(n_positions) +
                     " charging positions for animal " + str(animal_id))
        if n_positions > 0:
            if animal.name != None and len(animal.name) > 0:
                name = animal.name
            else:
                name = animal.imei
            positions = animal.filter_charging_positions(start, end)
            for position in positions:
                if int(position.battery) == position.battery:
                    position.battery = int(position.battery)
                fancy_date = get_fancy_time_from_utc(position.\
                                                    date, request=request)
                parameters = {
                    'animal_name': name,
                    'name': animal.user.email,
                    'imei': animal.imei,
                    'battery': str(position.battery),
                    'date': fancy_date,
                    'plot': animal.plot.name if animal.plot != None else '---'
                }
                popup_str = _("animal_popup_admin", domain='Ondestan',
                                  mapping=parameters)
                geojson.append({
                    "type": "Feature",
                    "properties": {
                        "id": animal.id,
                        "name": animal.name,
                        "imei": animal.imei,
                        "battery": position.battery,
                        "owner": animal.user.email,
                        "active": animal.active,
                        "outside": position.outside(),
                        "date": format_utcdatetime(position.date,
                                               request),
                        "fancy_date": fancy_date,
                        "popup": get_localizer(request).translate(
                                                            popup_str)
                    },
                    "geometry": eval(position.geojson)
                })
                # We return the max number of positions plus one, so it can
                # detect there are more and not just the barrier number
                if len(geojson) == (max_positions + 1):
                    logger.warning("Too many charging positions requested for animal "
                        + str(animal_id) + ", only the last "
                        + str(max_positions + 1) + " will be returned")
                    break
        else:
            geojson.append({
                "type": "Feature",
                "properties": {
                    "id": animal.id,
                    "name": animal.name,
                    "imei": animal.imei,
                    "battery": None,
                    "owner": animal.user.email,
                    "active": animal.active,
                    "outside": None,
                    "date": None,
                    "fancy_date": None,
                    "popup": None
                },
                "geometry": None
            })
    return geojson


@view_config(route_name='json_inactive_animals', renderer='json',
             permission='view')
def json_inactive_animals(request):
    json = []
    if (check_permission('admin', request)):
        animals = animal_service.get_inactive_animals()
        if animals != None:
            logger.debug("Found " + str(len(animals)) +
                         " inactive animals for all users")
            for animal in animals:
                json.append({
                    "id": animal.id,
                    "name": animal.name,
                    "owner": animal.user.email,
                })
        else:
            logger.debug("Found no inactive animals for any user")
    else:
        email = get_user_email(request)
        animals = animal_service.get_inactive_animals(email)
        if animals != None:
            logger.debug("Found " + str(len(animals)) +
                         " inactive animals for user " + email)
            for animal in animals:
                json.append({
                    "id": animal.id,
                    "name": animal.name,
                    "owner": animal.user.email,
                })
        else:
            logger.debug("Found no inactive animals for user " + email)
    return json


@view_config(route_name='json_plots', renderer='json',
             permission='view')
def json_plots(request):
    geojson = []
    if (check_permission('admin', request)):
        plots = plot_service.get_all_plots()
        if plots != None:
            logger.debug("Found " + str(len(plots)) + " plots for all users")
            for plot in plots:
                parameters = {
                    'plot_name': plot.name,
                    'name': plot.user.email
                }
                popup_str = _("plot_popup_admin", domain='Ondestan',
                              mapping=parameters)
                geojson.append({
                    "type": "Feature",
                    "properties": {
                        "id": plot.id,
                        "name": plot.name,
                        "owner": plot.user.email,
                        "centroid": eval(plot.centroid_geojson),
                        "popup": get_localizer(request).translate(popup_str)
                    },
                    "geometry": eval(plot.geojson)
                })
        else:
            logger.debug("Found no plots for any user")
    else:
        email = get_user_email(request)
        plots = plot_service.get_all_plots(email)
        if plots != None:
            logger.debug("Found " + str(len(plots)) + " plots " + \
                         "for user " + email)
            for plot in plots:
                parameters = {
                    'plot_name': plot.name,
                    'name': plot.user.email
                }
                popup_str = _("plot_popup", domain='Ondestan',
                              mapping=parameters)
                geojson.append({
                    "type": "Feature",
                    "properties": {
                        "id": plot.id,
                        "name": plot.name,
                        "owner": plot.user.email,
                        "centroid": eval(plot.centroid_geojson),
                        "popup": get_localizer(request).translate(popup_str)
                    },
                    "geometry": eval(plot.geojson)
                })
        else:
            logger.debug("Found no plots for user " + email)
    return geojson


@view_config(route_name='animals_list',
             renderer='templates/animalsList.pt',
             permission='view')
def animals_list(request):
    is_admin = check_permission('admin', request)
    if 'form.submitted' in request.params:
        if 'id' in request.params:
            user_id = None if is_admin else user_service.get_user_by_email(
                                            get_user_email(request)).id
            animal_id = int(request.params['id'])
            plot_id = None if request.params['plot'] == '' or\
                request.params['plot'] == None else int(request.params['plot'])
            animal_service.update_animal_plot(animal_id, plot_id, user_id)
    if is_admin:
        animals = animal_service.get_all_animals()
    else:
        email = get_user_email(request)
        animals = animal_service.get_all_animals(email)

    return dict(
        is_admin=is_admin,
        animals=animals,
        )


@view_config(route_name='device_configuration',
             renderer='templates/deviceConfiguration.pt',
             permission='view')
def device_configuration(request):
    animal_id = request.matchdict['animal_id']
    is_admin = check_permission('admin', request)
    email = get_user_email(request)
    animal = None
    if animal_id != None:
        try:
            animal = animal_service.get_animal_by_id(int(animal_id))
        except ValueError:
            pass
    if (animal == None) or (not is_admin and animal.user.email != email):
        return HTTPFound(request.route_url("animals_list"))
    if 'form.submitted' in request.params:
        if 'preconfig_nr' in request.params:
            preconfig_nr = int(request.params['preconfig_nr'])
            animal_service.save_new_preconfigured_configuration(preconfig_nr, animal)
        elif 'alarm_state' in request.params:
            if request.params['alarm_state'] == 'True':
                animal_service.activate_alarm_state(animal)
            else:
                animal_service.deactivate_alarm_state(animal)
        elif is_admin:
            animal_service.save_new_custom_configuration(request, animal)
    return dict(
        is_admin=is_admin,
        animal=animal,
        is_in_alarm_state=animal_service.is_in_alarm_state(animal),
        preconfig_names=get_device_preconfig_names(),
        current_config=get_device_config_fancy_description(animal.get_current_configuration(),
            request)
    )


@view_config(route_name='device_configuration_history',
             renderer='templates/deviceConfigurationHistory.pt',
             permission='view')
def device_configuration_history(request):
    animal_id = request.matchdict['animal_id']
    is_admin = check_permission('admin', request)
    email = get_user_email(request)
    animal = None
    if animal_id != None:
        try:
            animal = animal_service.get_animal_by_id(int(animal_id))
        except ValueError:
            pass
    if (animal == None) or (not is_admin and animal.user.email != email):
        return HTTPFound(request.route_url("animals_list"))
    configurations = Page(animal.get_all_configurations(),
        page=int(request.params.get('p', 1)),
        items_per_page=20,
        url=Customizable_PageURL_WebOb(request, get_param='p'))
    return dict(
        is_admin=check_permission('admin', request),
        configurations=configurations
        )


@view_config(route_name='nominatim_request_by_name', renderer='json',
             permission='view')
def nominatim_request_by_name(request):
    result = []
    if 'q' in request.GET:
        query = request.GET['q']
        logger_nominatim.info('Nominatim request: «' + query + '»')
        result = json.load(urllib2.urlopen('http://nominatim.openstreetmap.org/search?format=json&limit=5&email=' + Config.get_string_value('smtp.mail') + '&q=' + query))
    return result
