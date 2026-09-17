window.__CASES = (function(){
 const H=window.__H, C=H.circle, E=H.ellipse, L=H.line, PL=H.poly, A=H.arcSeg,
       R=H.rot, T=H.tr, S=H.sc, J=H.jit, NB=H.noisyBlob, mk=H.mk, P=H.P;
 function stick(cx, cy, armAng, legAng){
   // head, body, two arms from shoulder, two legs
   const sh=[cx, cy-40];
   return [ C(cx, cy-90, 34, 28),
            L(cx, cy-56, cx, cy+40, 14),
            R(L(sh[0],sh[1], sh[0]-90, sh[1]+40, 12), sh[0], sh[1], armAng),
            R(L(sh[0],sh[1], sh[0]+90, sh[1]+40, 12), sh[0], sh[1], -armAng),
            R(L(cx, cy+40, cx-55, cy+130, 12), cx, cy+40, legAng),
            R(L(cx, cy+40, cx+55, cy+130, 12), cx, cy+40, -legAng) ];
 }
 const cases = [];
 /* `expect` is the ORACLE: given the vocabulary the runner passes in, return
    the expectations this case makes beyond "it produced something on the
    canvas", which every case gets. They are stated against the POSES, so the
    same expectation is meaningful on the uniform row and on the hand-sampled
    one -- a number typed in here would only ever describe one of them. */
 function add(id, name, note, a, b, expect, hold){
   const A = mk(a); if (hold) A.hold = hold;
   cases.push({id:id, name:name, note:note, a:A, b:mk(b), expect:expect});
 }

 add('01','translation','circle slides right', [C(200,353,80,40)], [C(500,353,80,40)],
     E => [E.mid(), E.len(), E.pairs([0])]);
 add('02','rotation-anchor','arm rotates 70deg about a fixed shoulder',
     [ C(353,560,14,20), PL([[353,560],[353,300],[470,230]],14) ],
     [ C(353,560,14,20), R(PL([[353,560],[353,300],[470,230]],14),353,560, 70*Math.PI/180) ],
     E => [E.pairs([0,1]), E.len()]);
 add('03','scale','square grows 2.2x about centre',
     [PL([[280,280],[430,280],[430,430],[280,430],[280,280]],10)],
     [S(PL([[280,280],[430,280],[430,430],[280,430],[280,280]],10),355,355,2.0)],
     E => [E.mid(), E.len(), E.runs(1)]);
 add('04','bouncing-ball','ball high-left to floor-centre (arc expected)',
     [C(150,140,55,36)], [C(400,600,55,36)],
     E => [E.mid(), E.len()]);
 add('05','blinking-eye','open eye (lid arc + pupil) to closed (a line)',
     [ A(353,353,110,Math.PI,2*Math.PI,26), A(353,353,110,0,Math.PI,26), C(353,353,34,24) ],
     [ L(243,353,463,353,26), L(243,353,463,353,26), L(330,353,376,353,24) ],
     /* NOT a pairing: both lids close onto the SAME line on B, so the two
        candidates are identical and which one wins is settled by float noise
        -- the hand-sampled row picks [1,0,2] and renders identically, because
        the runs it chose between are the same run twice. Asking for [0,1,2]
        here asks for drawing order back, which pairing by shape exists to
        stop doing. */
     E => [E.runs(3)]);
 add('06','limb-pose','stick figure arms down to arms up',
     stick(353,330, 0, 0), stick(353,330, -1.9, 0.25),
     /* THE ARMS ARE MIRROR IMAGES and B's are crossed over the body, so the
        matcher pairs each with the one that ends up NEARER -- [0,1,3,2,4,5],
        the swap -- and the render is the better of the two readings: arms that
        stay on their own side rather than sweeping through the chest. Measured:
        the swap puts the tips at (274,346) and (432,346); drawing order puts
        both of them on the body's centre line. The expectation is the picture,
        not the index list. */
     E => [E.runs(6), E.mid()]);
 add('07','squash-stretch','tall ellipse to wide flat ellipse',
     [E(353,353,55,150,44)], [E(353,440,150,52,44)],
     E => [E.mid(), E.runs(1)]);
 /* 08 AND 09 ARE A MATCHED PAIR, and what they show is an asymmetry rather
    than a defect: an in-between is built by walking THIS page's strokes, so a
    stroke with no partner on the next page is carried through the middle, and
    a stroke with no partner on THIS one is not there yet. An object leaving
    lingers half way and then vanishes; an object arriving pops in at the end.
    Both are defensible for a single pose with no opacity to fade through, and
    the corpus's job is to say which one ships. Change one and the other has to
    move with it. */
 add('08','object-appears','circle alone, then circle + square — the square is NOT in the middle pose',
     [C(230,353,80,36)],
     [C(230,353,80,36), PL([[440,280],[580,280],[580,420],[440,420],[440,280]],8)],
     E => [E.runs(1)]);
 add('09','object-disappears','circle + square, then circle alone — the square IS in the middle pose',
     [C(230,353,80,36), PL([[440,280],[580,280],[580,420],[440,420],[440,280]],8)],
     [C(230,353,80,36)],
     E => [E.runs(2)]);
 add('10','two-cross','two circles swap places (they must pass through each other)',
     [C(180,353,62,36), C(530,353,62,36)],
     [C(530,353,62,36), C(180,353,62,36)],
     E => [E.mid(), E.len(), E.runs(2)]);
 add('11','stroke-order','same two shapes, drawn in the opposite order on B',
     [ PL([[150,250],[290,250],[290,390],[150,390],[150,250]],8), C(520,420,70,36) ],
     [ C(560,400,70,36), PL([[190,230],[330,230],[330,370],[190,370],[190,230]],8) ],
     E => [E.pairs([1,0]), E.runs(2)]);
 add('12','point-counts','circle 60 pts to same circle moved, 7 pts',
     [C(220,353,85,60)], [C(500,353,85,7)],
     E => [E.mid(), E.len(), E.pairs([0])]);
 add('13','messy-redraw','circle, then the same circle redrawn by hand (jitter, new radius)',
     [C(250,353,90,44)], [J(C(470,345,96,39,0.7),9,12345)],
     E => [E.mid(10), E.len(10)]);
 add('14','loop-start-point','closed loop, B starts half a turn round',
     [C(220,353,88,40,0,1)], [C(500,353,88,40,Math.PI,1)],
     E => [E.mid(), E.len(), E.runs(1)]);
 add('15','reversed-direction','closed loop, B drawn the other way round',
     [C(220,353,88,40,0,1)], [C(500,353,88,40,0,-1)],
     E => [E.mid(), E.len(), E.runs(1)]);
 add('16','large-motion','circle crosses the whole canvas',
     [C(100,100,58,36)], [C(610,610,58,36)],
     E => [E.mid(), E.len()]);
 add('17','tiny-motion','circle moves 6 px',
     [C(353,353,90,40)], [C(359,355,90,40)],
     E => [E.mid(), E.len()]);
 add('18','partial-erase','line with a rubbed-out middle, then moved',
     [ L(120,300,600,300,40), L(300,300,420,300,16).map(p=>Object.assign({},p,{erase:true,size:34})) ],
     [ L(120,430,600,430,40), L(300,430,420,430,16).map(p=>Object.assign({},p,{erase:true,size:34})) ],
     E => [E.erasers(1), E.runs(2)]);
 add('19','duplicate-shapes','three identical circles; only the middle one moves',
     [C(180,353,55,32), C(353,353,55,32), C(526,353,55,32)],
     [C(180,353,55,32), C(353,180,55,32), C(526,353,55,32)],
     E => [E.pairs([0,1,2]), E.mid(), E.len(), E.runs(3)]);
 add('20','multi-objects','three different shapes each moving differently',
     [ C(160,180,55,32), PL([[430,140],[570,140],[570,280],[430,280],[430,140]],8), L(120,560,320,560,20) ],
     [ C(300,300,55,32), R(PL([[430,140],[570,140],[570,280],[430,280],[430,140]],8),500,210,0.9), L(340,600,540,520,20) ],
     E => [E.pairs([0,1,2]), E.runs(3)]);
 add('21','noisy-contour','hand-drawn blob, redrawn by hand after moving',
     [NB(250,353,95,52,11,12)], [T(NB(250,353,95,52,29,12),210,25)],
     E => [E.mid(10), E.len(10)]);
 add('22','rotation-180','shape rotated a half-turn about its centre',
     [ PL([[260,300],[450,300],[450,340],[300,340],[300,410],[260,410],[260,300]],8) ],
     [ R(PL([[260,300],[450,300],[450,340],[300,340],[300,410],[260,410],[260,300]],8),353,353,Math.PI) ],
     E => [E.mid(), E.len()]);

 /* ---- v300: three cases an outside review of v299 asked for by name -------
    Each is a shape of input the corpus had no picture of, and each is a shape
    the code has actually been broken by. */

 // A TAP HAS NO EXTENT, and dividing by what it does not have is what put an
 // in-between's ink at x = 1.04e17 -- a page that reads as simply blank. All
 // three orders on one pair of pages: tap to tap, run to tap, tap to run.
 /* A TAP HAS NO EXTENT, and dividing by what it does not have is what put an
    in-between's ink at x = 1.04e17 -- a page that reads as simply blank.

    ONE RUN PER PAGE, DELIBERATELY. The first version of this case put all
    three pairs on one pair of pages, and the matcher paired the two LINES with
    each other and each tap with a tap: a perfectly ordinary render that never
    touched the degenerate path. Measured -- with ibFit's guard cut back to the
    one extent it tested before v299, the corpus stayed 25/25 green. A tap only
    meets a run when it is the only partner there is. */
 add('23','tap-degenerate','a tap, and the same tap moved — the middle pose has to carry it',
     [ [P(220,240)] ], [ [P(480,460)] ],
     E => [E.mid(), E.runs(1)]);
 add('23b','run-to-tap','a line collapsing to a tap — the fit has no extent on the far side',
     [ L(200,240,420,460,24) ], [ [P(500,300)] ],
     E => [E.runs(1)]);
 add('23c','tap-to-run','a tap opening into a line — the same fit, the other way round',
     [ [P(200,240)] ], [ L(380,300,600,520,24) ],
     E => [E.runs(1)]);

 // A PAGE HELD x4 IS ONE TAP AWAY on a fresh document, and the carve took one
 // slot off it however long it was held: the middle pose landed 250ms into a
 // 333ms interval instead of 167. The geometry was right and the timing was
 // not, which reads as a hang and then a flicker.
 add('24','long-hold','the first pose is held x4, so the carve has to split it evenly',
     [C(200,353,80,40)], [C(500,353,80,40)],
     E => [E.mid(), E.len(), E.holds(4)], 4);

 // THE SAME DRAWING, RECORDED BADLY. Both poses are the same L; the second is
 // taken at eight times the samples along two of its arms and a fifth along
 // the rest. Nothing about the drawing differs, so nothing about the middle
 // pose may. Deterministic, not fuzzed: the hand-sampled row already varies
 // the recording at random, and a case you cannot re-run is not a case.
 add('25','density-adversarial','identical geometry, one pose recorded lopsidedly',
     [PL([[200,200],[440,200],[440,260],[300,260],[300,400],[200,400]],16)],
     [ PL([[380,290],[620,290]],96).concat(
         PL([[620,290],[620,350],[480,350],[480,490],[380,490]],4).slice(1)) ],
     E => [E.mid(), E.len(), E.runs(1)]);

 return cases;
})();
