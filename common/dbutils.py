import logging
import time
import adsk.core, adsk.fusion

from math import pi, tan
import os
import traceback
from functools import wraps
from pprint import pformat
from collections import defaultdict, namedtuple

def timer(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        startTime = time.time()
        result = func(*args, **kwargs)
        logger.debug('{}: time taken = {}'.format(func.__name__, time.time() - startTime))
        return result
    return wrapper

# Generate occurrence hash
calcOccHash = lambda x: x.assemblyContext.name if x.assemblyContext else x.body.name

# Generate an edgeHash or faceHash from object
calcHash = lambda x: str(x.tempId) + ':' + x.assemblyContext.name.split(':')[-1] if x.assemblyContext else str(x.tempId) + ':' + x.body.name

getFaceNormal = lambda face: face.evaluator.getNormalAtPoint(face.pointOnFace)[1]
edgeVector = lambda coEdge:  coEdge.edge.evaluator.getEndPoints()[2].vectorTo(coEdge.edge.evaluator.getEndPoints()[1]) if coEdge.isOpposedToEdge else coEdge.edge.evaluator.getEndPoints()[1].vectorTo(coEdge.edge.evaluator.getEndPoints()[2]) 

#DbParams = namedtuple('DbParams', ['toolDia','dbType', 'fromTop', 'toolDiaOffset', 'offset', 'minimalPercent', 'longSide', 'minAngleLimit', 'maxAngleLimit' ])
logger = logging.getLogger('dogbone.utils')

def findInnerCorners(face):
    logger.debug('find Inner Corners')
    face1 = adsk.fusion.BRepFace.cast(face)
    if face1.objectType != adsk.fusion.BRepFace.classType():
        return False
    if face1.geometry.surfaceType != adsk.core.SurfaceTypes.PlaneSurfaceType:
        return False
    faceNormal = getFaceNormal(face)
    edgeList = []
    for loop in face1.loops:
        for coEdge in loop.coEdges:
            vertex = coEdge.edge.endVertex if coEdge.isOpposedToEdge else coEdge.edge.startVertex

            edges = vertex.edges
            
            edgeCandidates = list(filter(lambda x: x != coEdge.previous.edge and x != coEdge.edge, edges))
            if not len(edgeCandidates):
                continue
#                    if edges.count != 3:
#                        break
            dbEdge = getDbEdge(edgeCandidates, faceNormal, vertex)
            if dbEdge:
                edgeList.append(dbEdge)
            
    return edgeList

def getDbEdge(edges, faceNormal, vertex, minAngle = 1/360*pi*2, maxAngle = 179/360*pi*2):
    """
    orders list of edges so all edgeVectors point out of startVertex
    returns: list of edgeVectors
    """
    
#    refEdgeVector = refCoEdge.edge.endVertex.geometry.vectorTo(refCoEdge.edge.startVertex.geometry) if not refCoEdge.isOpposedToEdge else refCoEdge.edge.startVertex.geometry.vectorTo(refCoEdge.edge.endVertex.geometry)
    for edge in edges:
        edgeVector = correctedEdgeVector(edge, vertex)
        if edgeVector.angleTo(faceNormal) == 0:
            continue
        cornerAngle = getAngleBetweenFaces(edge)
#        logger.debug('corner angle = {}'.format(cornerAngle))
        return edge if cornerAngle < maxAngle and cornerAngle > minAngle else False
    return False


def getAngleBetweenFaces(edge):
    # Verify that the two faces are planar.
    face1 = edge.faces.item(0)
    face2 = edge.faces.item(1)
    if face1 and face2:
        if face1.geometry.objectType != adsk.core.Plane.classType() or face2.geometry.objectType != adsk.core.Plane.classType():
            return 0
    else:
        return 0

    # Get the normal of each face.
    ret = face1.evaluator.getNormalAtPoint(face1.pointOnFace)
    normal1 = ret[1]
    ret = face2.evaluator.getNormalAtPoint(face2.pointOnFace)
    normal2 = ret[1]
    # Get the angle between the normals.
    normalAngle = normal1.angleTo(normal2)

    # Get the co-edge of the selected edge for face1.
    if edge.coEdges.item(0).loop.face == face1:
        coEdge = edge.coEdges.item(0)
    elif edge.coEdges.item(1).loop.face == face1:
        coEdge = edge.coEdges.item(1)

    # Create a vector that represents the direction of the co-edge.
    if coEdge.isOpposedToEdge:
        edgeDir = edge.startVertex.geometry.vectorTo(edge.endVertex.geometry)
    else:
        edgeDir = edge.endVertex.geometry.vectorTo(edge.startVertex.geometry)

    # Get the cross product of the face normals.
    cross = normal1.crossProduct(normal2)

    # Check to see if the cross product is in the same or opposite direction
    # of the co-edge direction.  If it's opposed then it's a convex angle.
    if edgeDir.angleTo(cross) > pi/2:
        angle = (pi * 2) - (pi - normalAngle)
    else:
        angle = pi - normalAngle

    return angle

    
def createDogboneTool(edge, dbParams, topPlane = None):
    """
        returns temporary BRepBody - 
    
    """         

def findExtent(face, edge):
    
#    faceNormal = adsk.core.Vector3D.cast(face.evaluator.getNormalAtPoint(face.pointOnFace)[1])
    
    if edge.startVertex in face.vertices:
        endVertex = edge.endVertex
    else:
        endVertex = edge.startVertex
    return endVertex

    
def correctedEdgeVector(edge, refVertex):
    if edge.startVertex.geometry.isEqualTo(refVertex.geometry):
        return edge.startVertex.geometry.vectorTo(edge.endVertex.geometry)
    else:
        return edge.endVertex.geometry.vectorTo(edge.startVertex.geometry)
    return False

def correctedSketchEdgeVector(edge, refPoint):
    if edge.startSketchPoint.geometry.isEqualTo(refPoint.geometry):
        return edge.startSketchPoint.geometry.vectorTo(edge.endSketchPoint.geometry)
    else:
        return edge.endSketchPoint.geometry.vectorTo(edge.startSketchPoint.geometry)
    return False
    

def isEdgeAssociatedWithFace(face, edge):
    
    # have to check both ends - not sure which way around the start and end vertices are
    if edge.startVertex in face.vertices:
        return True
    if edge.endVertex in face.vertices:
        return True
    return False
    
def getCornerEdgesAtFace(face, edge):
    #not sure which end is which - so test edge ends for inclusion in face
    if edge.startVertex in face.vertices:
        startVertex = edge.startVertex
    else:
        startVertex = edge.endVertex 
    #edge has 2 adjacent faces - therefore the face that isn't from the 3 faces of startVertex, has to be the top face edges
#    returnVal = [edge1 for edge1 in edge.startVertex.edges if edge1 in face.edges]
    logger = logging.getLogger(__name__)
    returnVal = []
    for edge1 in startVertex.edges:
        if edge1 not in face.edges:
            continue
        logger.debug('edge {} added to adjacent edge list'.format(edge1.tempId))
        returnVal.append(edge1)
    if len(returnVal)!= 2:
        raise NameError('returnVal len != 2')
        
    return (returnVal[0], returnVal[1])
    
def getVertexAtFace(face, edge):
    if edge.startVertex in face.vertices:
        return edge.startVertex
    else:
        return edge.endVertex
    return False
    
def messageBox(*args):
    adsk.core.Application.get().userInterface.messageBox(*args)


def getTopFacePlane(faceEntity):
    normal = getFaceNormal(faceEntity)
    refPlane = adsk.core.Plane.create(faceEntity.vertices.item(0).geometry, normal)
    refLine = adsk.core.InfiniteLine3D.create(faceEntity.vertices.item(0).geometry, normal)
    refPoint = refPlane.intersectWithLine(refLine)
    faceList = []
    body = adsk.fusion.BRepBody.cast(faceEntity.body)
    for face in body.faces:
        if not normal.isParallelTo(getFaceNormal(face)):
            continue
        facePlane = adsk.core.Plane.create(face.vertices.item(0).geometry, normal)
        intersectionPoint = facePlane.intersectWithLine(refLine)
        directionVector = refPoint.vectorTo(intersectionPoint)
        distance = directionVector.dotProduct(normal)
        faceList.append([face, distance])
    sortedFaceList = sorted(faceList, key = lambda x: x[1])
    top = sortedFaceList[-1][0]
    return adsk.core.Plane.create(top.pointOnFace, getFaceNormal(top))

#    refPoint = top[0].nativeObject.pointOnFace if top[0].assemblyContext else top[0].pointOnFace
    
#    return topPlane
 

def getTranslateVectorBetweenFaces(fromFace, toFace):
#   returns absolute distance
    logger = logging.getLogger(__name__)

    normal = getFaceNormal(fromFace)
    if not normal.isParallelTo(getFaceNormal(fromFace)):
        return False

    fromFacePlane = adsk.core.Plane.create(fromFace.vertices.item(0).geometry, normal)
    fromFaceLine = adsk.core.InfiniteLine3D.create(fromFace.vertices.item(0).geometry, normal)
    fromFacePoint = fromFacePlane.intersectWithLine(fromFaceLine)
    
    toFacePlane = adsk.core.Plane.create(toFace.vertices.item(0).geometry, normal)
    toFacePoint = toFacePlane.intersectWithLine(fromFaceLine)
    translateVector = fromFacePoint.vectorTo(toFacePoint)
    return translateVector
        
    
class HandlerHelper(object):
    # Overloads notify method of handler Class
    def __init__(self):
        # Note: we need to maintain a reference to each handler, otherwise the handlers will be GC'd and SWIG will be
        # unable to call our callbacks. Learned this the hard way!
        self.handlers = []  # needed to prevent GC of SWIG objects

    def make_handler(self, handler_cls, notify_method, catch_exceptions=True):
        class _Handler(handler_cls):
            def notify(self, args):
                self.logger = logging.getLogger('dogbone.utils.error')
                if catch_exceptions:
                    try:
                        notify_method(args)
                    except:
                        messageBox('Failed:\n{}'.format(traceback.format_exc()))
                        self.logger.exception('error termination')
                        for handler in self.logger.handlers:
                            handler.flush()
                            handler.close()
                else:
                    notify_method(args)
        h = _Handler()
        self.handlers.append(h)
        return h
