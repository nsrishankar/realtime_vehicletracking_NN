# Utility functions for tiny_yolo obtained from Darkflow, Darknet, YAD2K.

import numpy as np
import cv2
import time
import pickle

class BoundingBox:
    def __init__(self):
        self.x, self.y = float(), float()
        self.w, self.h = float(), float()
        self.c = float()
        self.prob = float()

def overlap(x1,w1,x2,w2):
    l1 = x1 - w1 / 2.;
    l2 = x2 - w2 / 2.;
    left = max(l1, l2)
    r1 = x1 + w1 / 2.;
    r2 = x2 + w2 / 2.;
    right = min(r1, r2)
    return right - left;

def box_intersection(a, b):
    w = overlap(a.x, a.w, b.x, b.w);
    h = overlap(a.y, a.h, b.y, b.h);
    if w < 0 or h < 0: return 0;
    area = w * h;
    return area;

def box_union(a, b):
    i = box_intersection(a, b);
    u = a.w * a.h + b.w * b.h - i;
    return u;

def box_iou(a, b):
    return box_intersection(a, b) / box_union(a, b);

def load_weights(model,yolo_weight_file):           
    
    tiny_data = np.fromfile(yolo_weight_file,np.float32)[4:]
  
    index = 0
    for layer in model.layers:
        weights = layer.get_weights()
        if len(weights)>0:
            filter_shape, bias_shape = [w.shape for w in weights]
            if len(filter_shape)>2: #For convolutional layers
                filter_shape_i = filter_shape[::-1]
                bias_weight = tiny_data[index:index+np.prod(bias_shape)].reshape(bias_shape)
                index += np.prod(bias_shape)
                filter_weight= tiny_data[index:index+np.prod(filter_shape_i)].reshape(filter_shape_i)
                filter_weight= np.transpose(filter_weight,(2,3,1,0))
                index += np.prod(filter_shape)
                layer.set_weights([filter_weight,bias_weight])
            else: #For regular hidden layers
                bias_weight = tiny_data[index:index+np.prod(bias_shape)].reshape(bias_shape)
                index += np.prod(bias_shape)
                filter_weight= tiny_data[index:index+np.prod(filter_shape)].reshape(filter_shape)
                index += np.prod(filter_shape)
                layer.set_weights([filter_weight,bias_weight])
            
def yolo_net_out_to_car_boxes(net_out, threshold = 0.2, sqrt=1.8,C=20, B=2, S=7):
    class_num = 6
    boxes = []
    SS        =  S * S # number of grid cells
    prob_size = SS * C # class probabilities
    conf_size = SS * B # confidences for each grid cell
    
    probs = net_out[0 : prob_size]
    confs = net_out[prob_size : (prob_size + conf_size)]
    cords = net_out[(prob_size + conf_size) : ]
    probs = probs.reshape([SS, C])
    confs = confs.reshape([SS, B])
    cords = cords.reshape([SS, B, 4])
    
    for grid in range(SS):
        for b in range(B):
            bx   = BoundingBox()
            if np.isnan(cords[grid, b, 2] ** sqrt):
                bx.w = np.exp(cords[grid, b, 2] + sqrt)
            else:
                bx.w = cords[grid, b, 2] ** sqrt
            if np.isnan(cords[grid, b, 3] ** sqrt):
                bx.h = np.exp(cords[grid, b, 3] + sqrt)
            else:
                bx.h = cords[grid, b, 3] ** sqrt
            
            bx.c =  confs[grid, b]
            bx.x = (cords[grid, b, 0] + grid %  S) / S
            bx.y = (cords[grid, b, 1] + grid // S) / S

            p = probs[grid, :] * bx.c
            
            if p[class_num] >= threshold:
                bx.prob = p[class_num]
                boxes.append(bx)
                
    # combine boxes that overlap
    boxes.sort(key=lambda b:b.prob,reverse=True)
    for i in range(len(boxes)):
        boxi = boxes[i]
        if boxi.prob == 0: continue
        for j in range(i + 1, len(boxes)):
            boxj = boxes[j]
            if box_iou(boxi, boxj) >= .4:
                boxes[j].prob = 0.
    boxes = [b for b in boxes if b.prob > 0.]
    
    return boxes

def draw_box(boxes,im,crop_dim):
    imgcv = im
    [xmin,xmax] = crop_dim[0]
    [ymin,ymax] = crop_dim[1]
    for b in boxes:
        h, w, _ = imgcv.shape
        left  = int ((b.x - b.w/2.) * w)
        right = int ((b.x + b.w/2.) * w)
        top   = int ((b.y - b.h/2.) * h)
        bot   = int ((b.y + b.h/2.) * h)
        left = int(left*(xmax-xmin)/w + xmin)
        right = int(right*(xmax-xmin)/w + xmin)
        top = int(top*(ymax-ymin)/h + ymin)
        bot = int(bot*(ymax-ymin)/h + ymin)

        if left  < 0    :  left = 0
        if right > w - 1: right = w - 1
        if top   < 0    :   top = 0
        if bot   > h - 1:   bot = h - 1
        thick = int((h + w) // 150)
        cv2.rectangle(imgcv, (left, top), (right, bot), (255,0,0), thick)
        font = cv2.FONT_HERSHEY_SIMPLEX
        cv2.putText(imgcv, 'CAR', (left, top), font, 2, (255, 0, 255), 5, cv2.LINE_AA)
    return imgcv
