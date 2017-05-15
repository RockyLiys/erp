def create_thumbnail(img_org, img_new):
    try:
        import PIL.Image as Image
    except:
        return None

    try:
        im = Image.open(img_org)
    except IOError, e:
#        print "error to open", img_org, e.message
        return
    cur_width, cur_height = im.size
    new_width, new_height = 100,75
    if 0: #crop
        if cur_width < cur_height:
            ratio = float(new_width)/cur_width
        else:
            ratio = float(new_height)/cur_height
        x = (cur_width * ratio)
        y = (cur_height * ratio)
        x_diff = int(abs((new_width - x) / 2))
        y_diff = int(abs((new_height - y) / 2))
        box = (x_diff, y_diff, (x-x_diff), (y-y_diff))
        resized = im.resize((x, y), Image.ANTIALIAS).crop(box)
    else:
        if not new_width == 0 and not new_height == 0:
            if cur_width > cur_height:
                ratio = float(new_width)/cur_width
            else:
                ratio = float(new_height)/cur_height
        else:
            if new_width == 0:
                ratio = float(new_height)/cur_height
            else:
                ratio = float(new_width)/cur_width
        resized=im.resize((int(cur_width*ratio), int(cur_height*ratio)), Image.ANTIALIAS)
    try:
        os.makedirs(os.path.split(img_new)[0])
    except:
        pass
    resized.save(img_new)
#    print "save to:", img_new
    return img_new


