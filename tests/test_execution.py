import importlib.util
import base64
import io
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import patch

import torch
from PIL import Image


def module(name,**attrs):
    result=types.ModuleType(name); result.__dict__.update(attrs); sys.modules[name]=result; return result


class Progress:
    instances=[]
    def __init__(self,total,node_id=None): self.values=[]; self.total=total; Progress.instances.append(self)
    def update_absolute(self,value): self.values.append(value)


class Routes:
    def post(self,path): return lambda fn:fn


server=types.SimpleNamespace(routes=Routes(),client_id='owner',send_sync=lambda *args:None)
comfy=module('comfy')
comfy.model_management=module('comfy.model_management',throw_exception_if_processing_interrupted=lambda:None)
comfy.samplers=module('comfy.samplers',KSampler=types.SimpleNamespace(SAMPLERS=['euler'],SCHEDULERS=['simple']))
comfy.utils=module('comfy.utils',ProgressBar=Progress)
comfy.sample=module('comfy.sample',fix_empty_latent_channels=lambda model,latent:latent,
                    prepare_noise=lambda latent,seed,indices:indices,sample=None)
module('server',PromptServer=types.SimpleNamespace(instance=server))
root=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('smart_tile_final_test',root/'__init__.py',submodule_search_locations=[str(root)])
package=importlib.util.module_from_spec(spec); sys.modules[spec.name]=package; spec.loader.exec_module(package)
node_module=sys.modules['smart_tile_final_test.nodes']


class Model:
    def get_model_object(self,name):
        return types.SimpleNamespace(spacial_downscale_ratio=8) if name=='latent_format' else types.SimpleNamespace(patch=2)


class VAE:
    def spacial_compression_encode(self): return 8
    def encode(self,pixels): return pixels.movedim(-1,1).clone()
    def decode(self,latent): return latent.movedim(1,-1).unsqueeze(1)


class ExecutionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls): torch.set_num_threads(2)

    def options(self,**updates):
        result=dict(image=torch.rand(1,65,97,3),model=Model(),vae=VAE(),positive=object(),negative=object(),
                    upscale_by=1.5,columns=2,rows=2,expand_percent=15,redraw_mode='Independent tiles',seed=17,
                    steps=4,cfg=1,sampler_name='euler',scheduler='simple',denoise=.3,color_correction=False,unique_id='8')
        result.update(updates); return result

    def run_node(self,options):
        calls,events=[],[]; Progress.instances.clear()
        def sample(model,noise,steps,cfg,sampler,scheduler,positive,negative,latent,**kwargs):
            calls.append((noise,positive,negative,kwargs['disable_pbar']))
            for step in range(steps): kwargs['callback'](step,None,None,steps)
            return latent
        with patch.object(comfy.sample,'sample',sample), patch.object(server,'send_sync',lambda *args:events.append(args)):
            out=package.SmartTileRefine().refine(**options)
        return out,calls,events

    def test_schema_only_final_inputs(self):
        schema=package.SmartTileRefine.INPUT_TYPES()
        self.assertEqual(set(schema['optional']),{'upscale_model'})
        self.assertEqual(schema['required']['positive'],('CONDITIONING',))
        self.assertEqual(set(package.NODE_CLASS_MAPPINGS),{'SmartTileRefine'})
        for name in ('clip','captioner','global_prompt','negative_prompt','show_advanced','vae_tiled','tile_mode','upscale_method'):
            self.assertNotIn(name,schema['required'])

    def test_preview_png_retains_more_than_768_pixels(self):
        encoded=node_module.thumbnail(torch.zeros(1,900,600,3))
        data=base64.b64decode(encoded)
        self.assertTrue(data.startswith(b'\x89PNG'))
        self.assertEqual(Image.open(io.BytesIO(data)).size,(600,900))

    def test_odd_size_conditions_and_progress(self):
        options=self.options(); out,calls,events=self.run_node(options)
        self.assertTrue(torch.equal(options['image'],out['result'][0]))
        self.assertEqual([c[0] for c in calls],[[0],[1],[2],[3]])
        self.assertTrue(all(c[1] is options['positive'] and c[2] is options['negative'] and c[3] for c in calls))
        self.assertEqual(len(Progress.instances),1)
        values=Progress.instances[0].values
        self.assertEqual(values,sorted(values)); self.assertEqual(values[-1],1000)
        self.assertTrue(all(e[2]=='owner' for e in events))
        self.assertTrue(any(0<value<1 for e in events for value in (e[1].get('tile_progress') or {}).values()))

    def test_batch_and_snake(self):
        options=self.options(image=torch.rand(1,64,64,3),batch_size=4,expand_percent=50)
        out,calls,_=self.run_node(options)
        self.assertEqual([c[0] for c in calls],[[0,1,2,3]])
        self.assertTrue(torch.equal(out['result'][0],options['image']))
        options['redraw_mode']='S-shaped sequence'
        out,calls,_=self.run_node(options)
        self.assertEqual([c[0] for c in calls],[[0],[1],[3],[2]])
        self.assertTrue(torch.equal(out['result'][0],options['image']))

    def test_no_model_no_resize_even_when_factor_changes(self):
        options=self.options(model=None,vae=None,denoise=0,upscale_by=8)
        out,calls,_=self.run_node(options)
        self.assertFalse(calls); self.assertTrue(torch.equal(out['result'][0],options['image']))

    def test_connected_model_auto_enabled(self):
        options=self.options(denoise=0,upscale_model=object())
        with patch.object(node_module,'upscale_with_model',lambda model,image,w,h,update:node_module.resize(image,w,h)) as upscale:
            out,_,_=self.run_node(options)
        self.assertEqual(tuple(out['result'][0].shape),(1,98,146,3))
        self.assertTrue(out['ui']['smart_tile'][0]['settings']['upscale_connected'])

    def test_multiple_images_and_client_isolation(self):
        options=self.options(image=torch.rand(2,65,97,3))
        with patch.object(server,'client_id',None): out,calls,events=self.run_node(options)
        self.assertEqual([c[0] for c in calls],[[i] for i in range(8)])
        self.assertFalse(events); self.assertTrue(torch.equal(out['result'][0],options['image']))


if __name__=='__main__': unittest.main(verbosity=2)
