from pathlib import Path
import random
import sys
import unittest

import torch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from geometry import make_plan, target_size
from image_ops import TileMerger, color_correct, pad_tile


class CoreTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls): torch.set_num_threads(2)

    def test_random_exact_coverage(self):
        rng=random.Random(717)
        for _ in range(450):
            w,h=rng.randint(32,1800),rng.randint(32,1800)
            c,r=rng.randint(1,8),rng.randint(1,8)
            p=make_plan(w,h,c,r,rng.choice((0,1,15,50)))
            coverage=torch.zeros(h,w,dtype=torch.uint8)
            for t in p['tiles']:
                x,y,z,v=t['core']; a,b,d,e=t['crop']
                coverage[y:v,x:z]+=1
                self.assertTrue(0<=a<=x<z<=d<=w and 0<=b<=y<v<=e<=h)
            self.assertTrue(torch.all(coverage==1))

    def test_percentage_and_auto_upscale(self):
        p=make_plan(2400,1800,3,3,15)
        self.assertEqual(p['tiles'][4]['crop'],[680,510,1720,1290])
        self.assertEqual(target_size(255,383,1.5,True),(383,575))
        self.assertEqual(target_size(255,383,8,False),(255,383))

    def test_limits(self):
        self.assertEqual(make_plan(512,512,8,8)['count'],64)
        self.assertEqual(make_plan(512,512,1,1)['count'],1)
        for c,r in ((9,1),(0,2)):
            with self.assertRaises(ValueError): make_plan(512,512,c,r)
        self.assertEqual(make_plan(8192,8192,1,1)['tiles'][0]['crop'],[0,0,8192,8192])
        with self.assertRaises(ValueError): make_plan(8193,8193,1,1)

    def test_identity_and_four_way_overlap(self):
        for expansion in (0,1,15,50):
            source=torch.rand(1,257,389,3)
            p=make_plan(389,257,5,3,expansion)
            merger=TileMerger(source,p)
            for t in p['tiles']:
                x,y,z,v=t['crop']; merger.add(t,source[:,y:v,x:z])
            self.assertTrue(torch.equal(source,merger.finish()))
            self.assertGreater(merger.low_weight.min().item(),0)
            self.assertGreater(merger.high_weight.min().item(),0)

    def test_color_and_context(self):
        source=torch.full((1,257,389,3),0.4)
        p=make_plan(389,257)
        merger=TileMerger(source,p)
        t=p['tiles'][0]; x,y,z,v=t['crop']
        merger.add(t,source[:,y:v,x:z]+0.2)
        self.assertLessEqual(merger.context(p['tiles'][1]).max().item(),0.50001)
        self.assertLess((color_correct(source+0.1,source,.5)-source).abs().mean().item(),0.051)
        self.assertTrue(torch.equal(pad_tile(source[:,:67,:93],16)[:,:67,:93],source[:,:67,:93]))


if __name__=='__main__': unittest.main(verbosity=2)
