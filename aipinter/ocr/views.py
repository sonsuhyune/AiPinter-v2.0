from aipinter.ocr.hog import HOG 
import cv2
import os
import mahotas
from flask import render_template, url_for, redirect, flash, Blueprint, request
from aipinter.ocr.forms import OCRForm
from werkzeug.utils import secure_filename
from aipinter import ALLOWED_EXTENSIONS
from sklearn.externals import joblib
from aipinter.ocr import dataset
from aipinter.models import OCR
from aipinter import db

ocreg = Blueprint('ocreg', __name__)

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@ocreg.route('/ocr', methods=['POST', 'GET'])
def ocr():
    
    form = OCRForm()

    if request.method == 'POST':
        # check if the post request has the file part
        if 'file' not in request.files:
            flash('No file part', 'danger')
            return redirect(request.url)

        file = request.files['file']
        # if user does not select file, browser also
        # submit a empty part without filename
        if file.filename == '':
            flash('No selected file', 'danger')
            return redirect(request.url)


        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            image_path = os.path.join(os.getcwd() + '/aipinter/static/ocr_images', filename)
            file.save(image_path)
    

            model = joblib.load('aipinter/ocr/models_ocr/svm-top.cpickle')
            hog = HOG(orientations=18, pixelsPerCell=(10,10), cellsPerBlock=(1,1), transform=True)

            # image = cv2.imread(args['image'])
            image = cv2.imread(image_path)
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            blurred = cv2.GaussianBlur(gray, (5,5), 0)
            edged = cv2.Canny(blurred, 30, 150)
            im2, cnts, hierarcy = cv2.findContours(edged.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

            cnts = sorted([(c, cv2.boundingRect(c)[0]) for c in cnts], key = lambda x : x[1])

            for (c, _) in cnts:
                (x, y, w, h) = cv2.boundingRect(c)

                if w >= 7 and h >= 20:
                    roi = gray[y:y + h, x:x + w]
                    thresh = roi.copy()
                    T = mahotas.thresholding.otsu(roi)
                    thresh[thresh > T] = 255
                    thresh = cv2.bitwise_not(thresh)
                    thresh = dataset.deskew(thresh, 20)
                    thresh = dataset.center_extent(thresh, (20,20))
                    # cv2.imshow('thresh', thresh)
                    hist = hog.describe(thresh)
                    digit = model.predict([hist])[0]
                    # print('I think that number is : {}'.format(digit))

                    cv2.rectangle(image, (x, y), (x + w, y + h), (0, 255, 0), 1)
                    cv2.putText(image, str(digit), (x - 10, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0, 255, 0), 2)

            
            # flash('OCR is success', 'success')
            img_file_path = os.path.join(os.getcwd() + '/aipinter/static/ocr_images', filename)
            cv2.imwrite(img_file_path, image)

            ocr_img = OCR(image_file=img_file_path, description='this is ocr')
            db.session.add(ocr_img)
            db.session.commit()

            i = OCR.query.filter_by(id=ocr_img.id).first()
            return render_template('ocr.html', title='Vision',form=form, containers=i, os=os)    

    return render_template('ocr.html', title='Vision',form=form)     
