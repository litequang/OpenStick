"""Same-origin power controls, enabled only by the physical Linux portal."""
from flask import g,jsonify,render_template,request
from .device_power import ERRORS,validate


def register_power_routes(app,backend,token):
    app.extensions['device_power']=backend

    @app.before_request
    def power_transition_guard():
        if (request.method not in ('GET','HEAD','OPTIONS') and request.path!='/api/device/power'
                and request.path.startswith(('/api/','/files/'))):
            context=backend.activity()
            try:context.__enter__();g.power_activity=context
            except Exception as error:
                return jsonify(error=str(error) if str(error) in ERRORS else 'POWER_BUSY'),409

    @app.teardown_request
    def release_power_transition(error):
        context=g.pop('power_activity',None)
        if context:context.__exit__(None,None,None)

    @app.get('/settings/system')
    def power_page():return render_template('device_power.html',token=token,page='manage')

    @app.get('/api/device/power')
    def power_status():
        try:return jsonify(backend.status())
        except Exception as error:
            return jsonify(error=str(error) if str(error) in ERRORS else 'POWER_UNAVAILABLE'),503

    @app.post('/api/device/power')
    def power_action():
        value=request.get_json(silent=True)
        try:
            action=validate(value)
            return jsonify(backend.call(action,**{k:v for k,v in value.items() if k!='action'})),202
        except (ValueError,TypeError,AttributeError):return jsonify(error='INPUT_INVALID'),400
        except Exception as error:
            return jsonify(error=str(error) if str(error) in ERRORS else 'POWER_UNAVAILABLE'),409
        finally:
            if isinstance(value,dict):value.clear()
