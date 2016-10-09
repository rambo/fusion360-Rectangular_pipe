#Author-Eero 'rambo' af Heurlin
#Description-Create rectangular pipes

import adsk.core, adsk.fusion, adsk.cam, traceback


def create_pipe(selection, pipe_x_expr, pipe_y_expr, pipe_t_expr):
    ui = None
    rollback_objects = []
    try:
        app = adsk.core.Application.get()
        ui  = app.userInterface

        product = app.activeProduct
        design = adsk.fusion.Design.cast(product)
        if not design:
            ui.messageBox('It is not supported in current workspace, please change to MODEL workspace and try again.')
            return

        pipe_x = app.activeProduct.unitsManager.evaluateExpression(pipe_x_expr, 'mm')
        pipe_y = app.activeProduct.unitsManager.evaluateExpression(pipe_y_expr, 'mm')
        pipe_t = app.activeProduct.unitsManager.evaluateExpression(pipe_t_expr, 'mm')

        selObj = selection.entity
        
        comp = design.rootComponent
        
        # create path
        feats = comp.features
        chainedOption = adsk.fusion.ChainedCurveOptions.connectedChainedCurves
        if adsk.fusion.BRepEdge.cast(selObj):
            chainedOption = adsk.fusion.ChainedCurveOptions.tangentChainedCurves
        path = adsk.fusion.Path.create(selObj, chainedOption)
        path = feats.createPath(selObj)
        
        # create profile
        planes = comp.constructionPlanes
        planeInput = planes.createInput()
        planeInput.setByDistanceOnPath(selObj, adsk.core.ValueInput.createByReal(0))
        plane = planes.add(planeInput)
        rollback_objects.append(plane)
        
        sketches = comp.sketches
        sketch = sketches.add(plane)
        rollback_objects.append(sketch)
        
        center = plane.geometry.origin
        center = sketch.modelToSketchSpace(center)
        
        
        profile_lines = sketch.sketchCurves.sketchLines.addCenterPointRectangle(center, adsk.core.Point3D.create((center. x+ pipe_x/2), (center.y + pipe_y/2)))
        rollback_objects += list(profile_lines)
        profile = sketch.profiles[0]
        
        # create sweep
        sweepFeats = feats.sweepFeatures
        sweepInput = sweepFeats.createInput(profile, path, adsk.fusion.FeatureOperations.NewBodyFeatureOperation)
        sweepInput.orientation = adsk.fusion.SweepOrientationTypes.PerpendicularOrientationType
        sweepFeat = sweepFeats.add(sweepInput)
        rollback_objects.append(sweepFeat)
        
        # create shell
        startFaces = sweepFeat.startFaces
        endFaces = sweepFeat.endFaces
        
        objCol = adsk.core.ObjectCollection.create()
        for startFace in startFaces:
            objCol.add(startFace)
        for endFace in endFaces:
            objCol.add(endFace)
        
        shellFeats = feats.shellFeatures
        shellInput = shellFeats.createInput(objCol, False)
        shellInput.insideThickness = adsk.core.ValueInput.createByReal(pipe_t)
        shellFeat = shellFeats.add(shellInput)
        rollback_objects.append(shellFeat)
        

    except:
        for obj in rollback_objects[::-1]:
            obj.deleteMe()
        if ui:
            ui.messageBox('Failed:\n{}'.format(traceback.format_exc()))
    
    finally:
        app.activeViewport.refresh()



    
def run(context):
    ui = None
    try:
        app = adsk.core.Application.get()
        ui  = app.userInterface

        product = app.activeProduct
        design = adsk.fusion.Design.cast(product)
        if not design:
            ui.messageBox('It is not supported in current workspace, please change to MODEL workspace and try again.')
            return

        sel = ui.selectEntity('Select a path to create a pipe', 'Edges,SketchCurves')
        create_pipe(sel, '20mm', '30mm', '2mm')

    except:
        if ui:
            ui.messageBox('Failed:\n{}'.format(traceback.format_exc()))
