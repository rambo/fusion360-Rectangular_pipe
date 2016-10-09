#Author-Eero 'rambo' af Heurlin
#Description-Create rectangular pipes

import adsk.core, adsk.fusion, adsk.cam, traceback

handlers = []
app = adsk.core.Application.get()
ui = None
if app:
    ui = app.userInterface



def create_pipe(selObj, pipe_x_expr, pipe_y_expr, pipe_t_expr):
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

#        ui.messageBox('in create_pipe: pipe_x_expr %s' % repr(pipe_x_expr))
        pipe_x = app.activeProduct.unitsManager.evaluateExpression(pipe_x_expr, 'mm')
        pipe_y = app.activeProduct.unitsManager.evaluateExpression(pipe_y_expr, 'mm')
        pipe_t = app.activeProduct.unitsManager.evaluateExpression(pipe_t_expr, 'mm')

        
        comp = design.activeComponent
        
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
        app.activeViewport.refresh()
        
        sketches = comp.sketches
        sketch = sketches.add(plane)
        rollback_objects.append(sketch)
        
        center = plane.geometry.origin
        center = sketch.modelToSketchSpace(center)
        
        
        profile_lines = sketch.sketchCurves.sketchLines.addCenterPointRectangle(center, adsk.core.Point3D.create((center. x+ pipe_x/2), (center.y + pipe_y/2)))
        rollback_objects += list(profile_lines)
        app.activeViewport.refresh()
        profile = sketch.profiles[0]
        
        # create sweep
        sweepFeats = feats.sweepFeatures
        sweepInput = sweepFeats.createInput(profile, path, adsk.fusion.FeatureOperations.NewBodyFeatureOperation)
        sweepInput.orientation = adsk.fusion.SweepOrientationTypes.PerpendicularOrientationType
        sweepFeat = sweepFeats.add(sweepInput)
        rollback_objects.append(sweepFeat)
        app.activeViewport.refresh()
        
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
        app.activeViewport.refresh()
        

    except:
        for obj in rollback_objects[::-1]:
            obj.deleteMe()
            app.activeViewport.refresh()
        if ui:
            ui.messageBox('Failed:\n{}'.format(traceback.format_exc()))
    
    finally:
        app.activeViewport.refresh()


class RPipeCommandExecuteHandler(adsk.core.CommandEventHandler):
    def __init__(self):
        super().__init__()
    
    def notify(self, args):
        try:
            command = args.firingEvent.sender
            inputs = command.commandInputs

            pipe_x_expr = inputs.itemById('pipe_x_expr').expression
#            ui.messageBox('in RPipeCommandExecuteHandler: pipe_x_expr %s' % repr(pipe_x_expr))
            pipe_y_expr = inputs.itemById('pipe_y_expr').expression
            pipe_t_expr = inputs.itemById('pipe_t_expr').expression
            selections = []
            for i in range (0, inputs.itemById('curve_input').selectionCount ):
                selections.append( inputs.itemById('curve_input').selection(i).entity )

            for selection in selections:
                create_pipe(selection, pipe_x_expr, pipe_y_expr, pipe_t_expr)
            
            args.isValidResult = True

        except:
            if ui:
                ui.messageBox('Failed:\n{}'.format(traceback.format_exc()))



class RPipeCommandDestroyHandler(adsk.core.CommandEventHandler):
    def __init__(self):
        super().__init__()
    
    def notify(self, args):
        try:
            adsk.terminate()
        except:
            if ui:
                ui.messageBox('Failed:\n{}'.format(traceback.format_exc()))


class RPipeCommandCreatedHandler(adsk.core.CommandCreatedEventHandler):    
    def __init__(self):
        super().__init__()
        
    def notify(self, args):
        try:
            cmd = args.command
            cmd.isRepeatable = True
            onExecute = RPipeCommandExecuteHandler()
            cmd.execute.add(onExecute)
            #onExecutePreview = RPipeCommandExecuteHandler()
            #cmd.executePreview.add(onExecutePreview)
            onDestroy = RPipeCommandDestroyHandler()
            cmd.destroy.add(onDestroy)
            # keep the handler referenced beyond this function
            handlers.append(onExecute)
            #handlers.append(onExecutePreview)
            handlers.append(onDestroy)

            #define the inputs
            inputs = cmd.commandInputs
            # Create selection input
            curve_input = inputs.addSelectionInput('curve_input', 'Select', 'Select path')
            # select only curves
            curve_input.addSelectionFilter('SketchCurves')
            curve_input.addSelectionFilter('Edges')
            # I can select more than one curve
            curve_input.setSelectionLimits(1,0)

            inputs.addValueInput('pipe_x_expr', 'Pipe width', 'mm', adsk.core.ValueInput.createByReal(2) )
            inputs.addValueInput('pipe_y_expr', 'Pipe height', 'mm', adsk.core.ValueInput.createByReal(3) )
            inputs.addValueInput('pipe_t_expr', 'Wall thickness', 'mm', adsk.core.ValueInput.createByReal(.2) )

        except:
            if ui:
                ui.messageBox('Failed:\n{}'.format(traceback.format_exc()))


    
def run(context):
    try:
        commandDefinitions = ui.commandDefinitions
        #check the command exists or not
        cmdDef = commandDefinitions.itemById('RectangularPipe')
        if not cmdDef:
            cmdDef = commandDefinitions.addButtonDefinition('RectangularPipe', 'Create rectangular pipe', 'Create a rectangular pipe')
        
        onCommandCreated = RPipeCommandCreatedHandler()
        cmdDef.commandCreated.add(onCommandCreated)
        # keep the handler referenced beyond this function
        handlers.append(onCommandCreated)
        inputs = adsk.core.NamedValues.create()
        cmdDef.execute(inputs)
    
        # prevent this module from being terminate when the script returns, because we are waiting for event handlers to fire
        adsk.autoTerminate(False)
    except:
        if ui:
            ui.messageBox('Failed:\n{}'.format(traceback.format_exc()))