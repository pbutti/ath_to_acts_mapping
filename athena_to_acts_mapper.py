import csv
import argparse

import numpy as np
from scipy.spatial import KDTree

import json
import copy
import sys
import time


hgtd_z_limit = 3400


athena_map = {}


class moduleInfo:
    def __init__(self,
                 acts_id,
                 acts_ids, # the unpacked ids: [volume_id, boundary_id, layer_id, module_id]
                 athena_id,
                 athena_ids, #the unpacked ids: [bec,ld,etamod,phimod,side]
                 center):
        #print (acts_id)
        self.acts_id   = np.int64(acts_id)
        self.acts_ids  = acts_ids

        #print(athena_id)
        self.athena_id  = np.int64(int(athena_id, 16)) 
        self.athena_ids = athena_ids

        self.acts_vid = acts_ids[0]
        self.acts_bid = acts_ids[1]
        self.acts_lid = acts_ids[2]
        self.acts_mid = acts_ids[3]

        # Ensure center is an numpyarray with shape (3,)
        self.center = np.array(center,dtype=np.float64)
        if self.center.shape != (3,):
            raise ValueError("Center must be a 3D vector")



    def dump(self):
        print(self.acts_id,self.athena_id,self.athena_ids,self.acts_ids, self.center)

#geometry_id,volume_id,boundary_id,layer_id,module_id,cx,cy,cz,rot_xu,rot_xv,rot_xw,rot_yu,rot_yv,rot_yw,rot_zu,rot_zv,rot_zw,bounds_type, 
#bound_param0,bound_param1,bound_param2,bound_param3,bound_param4,bound_param5,bound_param6,module_t,pitch_u,pitch_v

#144115325514809600,2,0,2,1,-133.082291,-13.9184942,-3468.89502

def process_acts_csv(input_path,
                     acts_map,
                     doHgtd=False):

    acts_map   = {}
    
    with open(input_path, 'r') as input_file:
        reader = csv.reader(input_file)

        #Skip first row
        next(reader)
        
        for row in reader:
            out = row[:8]
            if (not doHgtd):
                if abs(float(out[-1])) > hgtd_z_limit:
                    continue

            m = moduleInfo(out[0],
                           out[1:5],
                           "0x0",
                           [],
                           out[5:])
                

            acts_map[out[0]] = m


    return acts_map


#volume_id,boundary_id,layer_id,approach_id,sensitive_id,event_id,athena_id,bec,ld,etam,phim,side,cx,cy,cz
#8,0,2,1,9196,0,0x40440000000000,-2,2,22,0,0,-30.9326,95.2008,-2623



def process_athena_csv(input_path,
                       athena_map,
                       doHgtd=False):

    athena_map = {}
    
    with open(input_path,'r') as input_file:
        reader = csv.reader(input_file)

        #Skip first row
        next(reader)

        for row in reader:
            out = row[0:]
            if (not doHgtd):
                if abs(float(out[-1])) > hgtd_z_limit:
                    continue

            
            m = moduleInfo(0,
                           [out[0],out[1],out[2],out[4]],
                           out[6],
                           out[7:12],
                           out[12:])
                
            athena_map[out[6]] = m
                
        return athena_map




# 3/6/24 Checked for overlaps for ITk geometry v3. None found. Can disable by def
    
def main():
    parser = argparse.ArgumentParser(description="Retrieve the location and ids from the athena and acts geometries.")
    parser.add_argument('--input_acts', help="Path to the acts input CSV file")
    parser.add_argument('--input_athena', help="Path to the athena input CSV file")
    parser.add_argument('--hgtd',help="Remove hgtd elements from the parsing",default=False,action="store_true")
    parser.add_argument('--output_json',help="Output json where to store the mapping",default="matched_map.json")
    parser.add_argument('--kdtree',help="Use K-d tree. The maps of the geometries contain 60k elements. Advise to use", default=True, action="store_true")
    parser.add_argument('--tolerance',help="The tolerance for matching elements in the maps in mm. 5 mm seems to match them all",default=5.)
    parser.add_argument('--checkOverlap',help="Toggle checking if there two elements in the acts map match to the athena map. You can check it only once to save O(n) operations.",default=False, action="store_true")
    
                        
    args = parser.parse_args()
    
    acts_map = process_acts_csv(args.input_acts,args.hgtd)

    print("ACTS MAPPING")
    c = 0
    for k in acts_map.keys():
        c+=1
        acts_map[k].dump()
        if (c==10):
            break;



    athena_map = process_athena_csv(args.input_athena,args.hgtd)

    print("ATHENA MAPPING")
    
    c=0
    for k in athena_map.keys():
        c+=1
        athena_map[k].dump()
        if (c==10):
            break



    athena_map_copy = athena_map.copy()
    skip_dict = {}
        
    matched_map   = {}
    unmatched_map = {}


    print("Configuration")
    print(args)

    # Start time
    start_time = time.time()
    
    # Ordinary algorithm looping on all the elements of the maps.
    if not args.kdtree:
    
        c = 0
        for acts_key,value in acts_map.items():

            if (c % 100 == 0):
                print ("checking entry=",c,value.center)
            out = []
        
            notFound = True
            c+=1
            acts_loc = value.center
            
            for athena_key,value2 in athena_map_copy.items():

                #print(value.center)
                #print(value2.center)

                if athena_key in skip_dict:
                    continue;
            
                if np.linalg.norm(value.center - value2.center) < args.tolerance :

                    out = {"acts_id": acts_key,
                           "athena_id": athena_key,
                           "athena_ids" : value2.athena_ids}
                
                    #map it with the athena ID
                    matched_map[int(athena_key,16)] = out
                    skip_dict[athena_key] = True
                    notFound = False
                    continue

            if notFound:
                unmatched_map[acts_key] = value.center

    #Use the k-d tree search algorithm
    else: 

        print("Using K-D tree algorithm")
        # Extract 3D vectors from custom objects
        centers = [obj.center for obj in athena_map.values()]
        
        # Construct k-d tree
        kdtree = KDTree(centers)

        # Find nearest neighbors from dict1 to dict2
        matching_keys     = []
        non_matching_keys = []

        for key, value in acts_map.items():
            vec = value.center
            dist, idx = kdtree.query(vec)
            
            if dist < args.tolerance:
                if args.checkOverlap:
                    if (key in list(athena_map.keys())):
                        raise ValueError("The maps have overlapping surfaces")
                
                matching_keys.append((key, list(athena_map.keys())[idx]))
            else:
                non_matching_keys.append([key,value.center])



    # End time
    end_time = time.time()

    # Time taken
    elapsed_time = end_time - start_time
    print(f"Time taken: {elapsed_time} seconds")

    matched_map = {}
    
    for acts_key,athena_key in matching_keys:
        out = {"acts_id"    : acts_key,
               "athena_id"  : athena_key,
               "athena_ids" : athena_map[athena_key].athena_ids}
        
        matched_map[int(athena_key,16)] = out
        
    # Dump data to JSON with indentation
    json_data = json.dumps(matched_map, indent=4)
    
    # Write JSON data to a file
    with open(args.output_json, "w") as json_file:
        json_file.write(json_data)
    
    print("Matching keys:", len(matching_keys))
    print("Non Matching keys", len(non_matching_keys))

                
             
if __name__=="__main__":
    main()
