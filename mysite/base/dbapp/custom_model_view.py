# coding=utf-8
from django.contrib.auth.decorators import login_required
from mysite.base.dbapp.datautils import NoFound404Response
from traceback import print_exc
from django.utils.translation import ugettext as _
from django.shortcuts import render_to_response
from django.template import loader, RequestContext, Template, TemplateDoesNotExist
from mysite.base.dbapp.utils import getJSResponse

from mysite.base.dbapp.urls import dbapp_url
from erp.settings import MEDIA_ROOT
from mysite.base import get_all_app_and_models
from mysite.base.custom_model import GridModel
from django.utils.encoding import smart_str
from django.utils.simplejson import dumps
from mysite.base import get_all_app_and_models
from mysite.api.grid_export import ExportGrid


@login_required
def GridModelView(request, app_label, model_name):
    apps = get_all_app_and_models(hide_visible_false=False)
    model_dic = None
    try:
        for e in apps:
            if e[0] == app_label:
                app = e[1]
                for m in app["models"]:
                    if m["name"] == model_name:
                        model_dic = m
                        break
                break
    except:
        return NoFound404Response(request)
    if model_dic and model_dic.has_key('page') and issubclass(model_dic['page'], GridModel):
        try:
            try:
                offset = int(request.REQUEST.get('page', 1))
            except:
                offset = 1
            try:
                psize = int(request.REQUEST.get('rp', 15))
            except:
                psize = 15
            arg = {'offset': offset, 'psize': psize}
            sortname = request.REQUEST.get('sortname', 'undefined')
            sortorder = request.REQUEST.get('sortorder', 'undefined')
            if sortname != 'undefined':
                arg['sortname'] = sortname
                arg['sortorder'] = (sortorder == 'undefined') and 'asc' or sortorder
            query = request.REQUEST.get('query', '')
            qtype = request.REQUEST.get('qtype', '')
            if query != '':
                arg['query'] = query
                arg['qtype'] = qtype
            grid_model = model_dic['page'](request)
            #            grid_model.grid.ParseArg(**arg)
            if request.REQUEST.has_key("export"):
                return GridExport(request, grid_model, **arg)
            else:
                return GridView(request, grid_model, **arg)
        except:
            print_exc()
            raise
    else:
        return NoFound404Response(request)


def GridView(request, grid_model, **arg):
    m_grid = grid_model.grid
    grid_model.SetPageSize(arg['psize'])
    grid_model.MakeData(request, **arg)
    grid_model.grid.ParseArg(**arg)
    if not grid_model._paged:
        grid_model.Paging(arg['offset'])
    ret = m_grid.ResultDic()
    return getJSResponse(smart_str(dumps(ret)))


def GridExport(request, grid_model, **arg):
    m_grid = grid_model.grid

    hide_index = request.REQUEST.get('hide', None)
    if hide_index:
        m_hide_index = [int(e) for e in hide_index.split(',')]
    else:
        m_hide_index = []
    grid_model.SetPageSize(0)
    grid_model.MakeData(request, **arg)
    grid_model.grid.ParseArg(**arg)
    if not grid_model._paged:
        grid_model.Paging(1)
    ret = m_grid._GetData(m_hide_index)
    head = {}
    field = []
    i = 0
    for e in m_grid.dic:
        if i in m_hide_index:
            pass
        else:
            head[e[0]] = e[1]
            field.append(e[0])
        i += 1
    ret.insert(0, head)
    ret.insert(0, field)
    return ExportGrid(request, ret)


#    return getJSResponse(smart_str(dumps(ret)))

@login_required
def AppPageView(request, app_label, model_name):
    apps = get_all_app_and_models(hide_visible_false=False)
    model_dic = None
    try:
        for e in apps:
            if e[0] == app_label:
                app = e[1]
                for m in app["models"]:
                    if m["name"] == model_name:
                        model_dic = m
                        break
                break
    except:
        return NoFound404Response(request)
    if model_dic and model_dic.has_key('page'):
        try:
            return PageView(request, app["models"][0]["app_label"], model_dic)
        except:
            print_exc()
            raise
    else:
        return NoFound404Response(request)


def PageView(request, app_name, model):
    page = model["page"](request)
    menu_group = page.app_menu
    PageName = page.__class__.__name__

    if request.REQUEST.has_key("pure"):
        m_urlparams = dict(request.GET)
        del m_urlparams["pure"]
        m_params = []
        for e in m_urlparams.keys():
            m_value = m_urlparams[e]
            if type(m_value) == type([]):
                m_value = ','.join(m_value)
            m_params.append({"name": str(e), "value": str(m_value)})
        #        if not m_params:
        #            m_params = '[]'
        response_context = {
            'app_label': menu_group,
            'model_name': PageName,
            'urlparams': m_params,
            'select_fieldname': request.GET.get('fieldname', ''),
            'ids': request.GET.get('ids', ''),
            'verbose_name': page.verbose_name}
    #        if not page.template.endswith('_window.html'):
    #            page.template = page.template.replace(".html","_pure.html")
    else:
        apps = get_all_app_and_models()
        app = dict(apps)[app_name]
        request.dbapp_url = dbapp_url
        position = _(u'%s->%s' % (app["name"], page.verbose_name))
        response_context = {
            'dbapp_url': dbapp_url,
            'MEDIA_URL': MEDIA_ROOT,
            "current_app": menu_group,
            "myapp": app,
            'apps': apps,
            'app_label': menu_group,
            'model_name': PageName,
            'menu_focus': PageName,
            'position': position,
            'verbose_name': page.verbose_name
        }
    if page.context:
        if callable(page.context):
            response_context.update(page.context())
        else:
            response_context.update(page.context)
    return render_to_response(page.template,
                              RequestContext(request, response_context)
                              )
