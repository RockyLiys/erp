from django.conf import settings
import os
from base.options import options

def get_model_filename(model, fname="", catalog=None):
        fname="model/%s/%s%s"%(\
                model._meta.app_label+'.'+model.__name__, 
                catalog and catalog+"/" or "",
                fname or "")
        return (settings.ADDITION_FILE_ROOT+fname, settings.ADDITION_FILE_URL+"/"+fname)

def save_model_file(model, fname, raw_data, catalog=None, overwrite=True):
        fns=get_model_filename(model, fname, catalog)
        fn=os.path.split(fns[0])
        try:
                os.makedirs(fn[0])
        except: pass
        f=file(fns[0], "w+b")
        f.write(raw_data)
        f.close()
        return fns[1]


def get_model_image(model, fname, catalog="photo", check_exist=False):
        fns=get_model_filename(model, fname, catalog)
        fnst=get_model_filename(model, fname, catalog+"_thumbnail")
        if check_exist: 
                return (os.path.exists(fns[0]) and fns[0] or None, fns[1], 
                        os.path.exists(fnst[0]) and fnst[0] or None, fnst[1])
        return (fns[0], fns[1], fnst[0], fnst[1])
                
def save_model_image_from_request(request, requestName, model, file_name, catalog='photo'):
        print "save_model_image_from_request"
        import StringIO
        from image import create_thumbnail
        fns=get_model_filename(model, file_name, catalog)
        fname=fns[0]
        fn=os.path.split(fname)
        try:
                os.makedirs(fn[0])
        except: pass
        output = StringIO.StringIO()
        try:
                f=request.FILES[requestName]
        except:
                print requestName, request
                import traceback; traceback.print_exc()
                return None
        for chunk in f.chunks():
                output.write(chunk)
        output.seek(0)
        try:
                import PIL.Image as Image
        except Exception, e:
                import traceback; traceback.print_exc()
                f=file(fname, "w+b")
                f.write(output.read())
                f.close()
                return 200
        try:
                im = Image.open(output)
        except IOError, e:
                return getJSResponse("result=-1; message='Not a valid image file';")
        #print f.name
        size=f.size
        max_width=int(options["dbapp.max_photo_width"])
        if im.size[0]>max_width:
                width=max_width
                height=int(im.size[1]*max_width/im.size[0])
                im=im.resize((width, height), Image.ANTIALIAS)
        try:
                im.save(fname);
        except IOError:
                im.convert('RGB').save(fname)
        
        fns=get_model_filename(model, file_name, catalog+"_thumbnail")
        fn=os.path.split(fns[0])
        try:
                os.makedirs(fn[0])
        except: pass
        create_thumbnail(fname, fns[0])
        return size        


