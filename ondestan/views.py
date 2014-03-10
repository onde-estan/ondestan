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

from .security import get_user_login, check_permission
from .services import plot_service, cow_service, user_service
import logging

logger = logging.getLogger('ondestan')

@view_config(route_name='login', renderer='templates/login.pt')
@forbidden_view_config(renderer='templates/login.pt')
def login(request):
    login_url = request.route_url('login')
    referrer = request.url
    if referrer == login_url:
        referrer = '/' # never use the login form itself as came_from
    came_from = request.params.get('came_from', referrer)
    message = ''
    login = ''
    if 'form.submitted' in request.params:
        login = request.params['login']
        if user_service.check_login_request(request):
            headers = remember(request, login)
            return HTTPFound(location = came_from,
                             headers = headers)
        message = 'Failed login'

    return dict(
        message = message,
        url = request.application_url + '/login',
        came_from = came_from,
        login = login,
        )

@view_config(route_name='signup', renderer='templates/signup.pt')
def signup(request):
    message = ''
    login = ''
    name = ''
    email = ''
    phone = ''
    if 'form.submitted' in request.params:
        if user_service.create_user(request):
            raise HTTPFound(request.route_url("signup_success"))
        message = 'Login is already in use. Please choose a different one.'
        login = request.params['login']
        name = request.params['name']
        email = request.params['email']
        phone = request.params['phone']

    return dict(
        message = message,
        url = request.application_url + '/signup',
        login = login,
        name = name,
        email = email,
        phone = phone,
        )

@view_config(route_name='signup_success', renderer='templates/signupSuccess.pt')
def signup_success(request):
    return dict()

@view_config(route_name='logout')
def logout(request):
    headers = forget(request)
    return HTTPFound(location = request.route_url('login'),
                     headers = headers)

@view_config(route_name='activate_user')
def activate_usr(request):
    loginhash = request.matchdict['loginhash']
    user_service.activate_user(loginhash)
    return HTTPFound(location = request.route_url('login'))

@view_config(route_name='map', renderer='templates/simpleViewer.pt',
             permission='view')
def viewer(request):
    return dict(project= u'Ondestán',
                user_id=get_user_login(request),
                can_edit=check_permission('edit', request),
                is_admin=check_permission('admin', request))

@view_config(route_name='default')
def default(request):
    raise HTTPFound(request.route_url("map"))

@view_config(route_name='json_cows', renderer='json',
             permission='view')
def json_cows(request):
    geojson = []
    if (check_permission('admin', request)):
        cows = cow_service.get_all_cows()
        if cows != None:
            logger.debug("Found " + str(len(cows)) + " cows for all users")
            for cow in cows:
                geojson.append({
                "type": "Feature",
                "properties": {
                    "name": cow.name,
                    "battery_level": cow.battery_level,
                    "owner": cow.user.login,
                    "outside": cow.outside,
                    "popup": cow.name + " (" + str(cow.battery_level) + "%), property of " + cow.user.name + " (" + cow.user.login + ")"
                },
                "geometry": eval(cow.geojson)
                });
        else:
            logger.debug("Found no cows for any user")
    else:
        login = get_user_login(request)
        cows = cow_service.get_cow_by_user_login(login)
        if cows != None:
            logger.debug("Found " + str(len(cows)) + " cows for user " + login)
            for cow in cows:
                geojson.append({
                "type": "Feature",
                "properties": {
                    "name": cow.name,
                    "battery_level": cow.battery_level,
                    "owner": cow.user.login,
                    "outside": cow.outside,
                    "popup": cow.name + " (" + str(cow.battery_level) + "%)"
                },
                "geometry": eval(cow.geojson)
                });
        else:
            logger.debug("Found no cows for user " + login)
    return geojson;

@view_config(route_name='json_plots', renderer='json',
             permission='view')
def json_plots(request):
    geojson = []
    if (check_permission('admin', request)):
        plots = plot_service.get_all_plots()
        if plots != None:
            logger.debug("Found " + str(len(plots)) + " plots for all users")
            for plot in plots:
                geojson.append({
                "type": "Feature",
                "properties": {
                    "name": plot.name,
                    "owner": plot.user.login,
                    "popup": plot.name + " property of " + plot.user.name + " (" + plot.user.login + ")"
                },
                "geometry": eval(plot.geojson)
                });
        else:
            logger.debug("Found no plots for any user")
    else:
        login = get_user_login(request)
        plots = plot_service.get_plot_by_user_login(login)
        if plots != None:
            logger.debug("Found " + str(len(plots)) + " plots for user " + login)
            for plot in plots:
                geojson.append({
                "type": "Feature",
                "properties": {
                    "name": plot.name,
                    "owner": plot.user.login,
                    "popup": plot.name
                },
                "geometry": eval(plot.geojson)
                });
        else:
            logger.debug("Found no plots for user " + login)
    return geojson;
