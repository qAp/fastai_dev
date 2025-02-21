#AUTOGENERATED! DO NOT EDIT! File to edit: dev/03a_layers.ipynb (unless otherwise specified).

__all__ = ['Identity', 'Lambda', 'PartialLambda', 'View', 'ResizeBatch', 'Flatten', 'Debugger', 'sigmoid_range',
           'SigmoidRange', 'AdaptiveConcatPool2d', 'PoolType', 'pool_layer', 'PoolFlatten', 'NormType', 'BatchNorm',
           'BatchNorm1dFlat', 'LinBnDrop', 'init_default', 'ConvLayer', 'AdaptiveAvgPool', 'MaxPool', 'AvgPool',
           'BaseLoss', 'CrossEntropyLossFlat', 'BCEWithLogitsLossFlat', 'BCELossFlat', 'MSELossFlat',
           'LabelSmoothingCrossEntropy', 'trunc_normal_', 'Embedding', 'SelfAttention', 'PooledSelfAttention2d',
           'SimpleSelfAttention', 'icnr_init', 'PixelShuffle_ICNR', 'SequentialEx', 'MergeLayer', 'Cat', 'SimpleCNN',
           'ResBlock', 'swish', 'Swish', 'MishJitAutoFn', 'mish', 'MishJit', 'ParameterModule',
           'children_and_parameters', 'TstModule', 'tst', 'children', 'flatten_model', 'NoneReduce', 'in_channels']

#Cell
from .core.all import *
from .torch_imports import *
from .torch_core import *
from .test import *
from torch.nn.utils import weight_norm, spectral_norm

#Cell
class Identity(Module):
    "Do nothing at all"
    def forward(self,x): return x

#Cell
class Lambda(Module):
    "An easy way to create a pytorch layer for a simple `func`"
    def __init__(self, func): self.func=func

    def forward(self, x): return self.func(x)
    def __repr__(self): return f'{self.__class__.__name__}({self.func})'

#Cell
class PartialLambda(Lambda):
    "Layer that applies `partial(func, **kwargs)`"
    def __init__(self, func, **kwargs):
        super().__init__(partial(func, **kwargs))
        self.repr = f'{func.__name__}, {kwargs}'

    def forward(self, x): return self.func(x)
    def __repr__(self): return f'{self.__class__.__name__}({self.repr})'

#Cell
class View(Module):
    "Reshape `x` to `size`"
    def __init__(self, *size): self.size = size
    def forward(self, x): return x.view(self.size)

#Cell
class ResizeBatch(Module):
    "Reshape `x` to `size`, keeping batch dim the same size"
    def __init__(self, *size): self.size = size
    def forward(self, x): return x.view((x.size(0),) + self.size)

#Cell
class Flatten(Module):
    "Flatten `x` to a single dimension, often used at the end of a model. `full` for rank-1 tensor"
    def __init__(self, full=False): self.full = full
    def forward(self, x): return x.view(-1) if self.full else x.view(x.size(0), -1)

#Cell
class Debugger(nn.Module):
    "A module to debug inside a model."
    def forward(self,x):
        set_trace()
        return x

#Cell
def sigmoid_range(x, low, high):
    "Sigmoid function with range `(low, high)`"
    return torch.sigmoid(x) * (high - low) + low

#Cell
class SigmoidRange(Module):
    "Sigmoid module with range `(low, high)`"
    def __init__(self, low, high): self.low,self.high = low,high
    def forward(self, x): return sigmoid_range(x, self.low, self.high)

#Cell
class AdaptiveConcatPool2d(nn.Module):
    "Layer that concats `AdaptiveAvgPool2d` and `AdaptiveMaxPool2d`"
    def __init__(self, size=None):
        super().__init__()
        self.size = size or 1
        self.ap = nn.AdaptiveAvgPool2d(self.size)
        self.mp = nn.AdaptiveMaxPool2d(self.size)
    def forward(self, x): return torch.cat([self.mp(x), self.ap(x)], 1)

#Cell
mk_class('PoolType', **{o:o for o in 'Avg Max Cat'.split()})

#Cell
def pool_layer(pool_type):
    return nn.AdaptiveAvgPool2d if pool_type=='Avg' else nn.AdaptiveMaxPool2d if pool_type=='Max' else AdaptiveConcatPool2d

#Cell
class PoolFlatten(nn.Sequential):
    "Combine `nn.AdaptiveAvgPool2d` and `Flatten`."
    def __init__(self, pool_type=PoolType.Avg): super().__init__(pool_layer(pool_type)(1), Flatten())

#Cell
NormType = Enum('NormType', 'Batch BatchZero Weight Spectral')

#Cell
def BatchNorm(nf, norm_type=NormType.Batch, ndim=2, **kwargs):
    "BatchNorm layer with `nf` features and `ndim` initialized depending on `norm_type`."
    assert 1 <= ndim <= 3
    bn = getattr(nn, f"BatchNorm{ndim}d")(nf, **kwargs)
    bn.bias.data.fill_(1e-3)
    bn.weight.data.fill_(0. if norm_type==NormType.BatchZero else 1.)
    return bn

#Cell
class BatchNorm1dFlat(nn.BatchNorm1d):
    "`nn.BatchNorm1d`, but first flattens leading dimensions"
    def forward(self, x):
        if x.dim()==2: return super().forward(x)
        *f,l = x.shape
        x = x.contiguous().view(-1,l)
        return super().forward(x).view(*f,l)

#Cell
class LinBnDrop(nn.Sequential):
    "Module grouping `BatchNorm1d`, `Dropout` and `Linear` layers"
    def __init__(self, n_in, n_out, bn=True, p=0., act=None, lin_first=False):
        layers = [BatchNorm(n_out if lin_first else n_in, ndim=1)] if bn else []
        if p != 0: layers.append(nn.Dropout(p))
        lin = [nn.Linear(n_in, n_out, bias=not bn)]
        if act is not None: lin.append(act)
        layers = lin+layers if lin_first else layers+lin
        super().__init__(*layers)

#Cell
def init_default(m, func=nn.init.kaiming_normal_):
    "Initialize `m` weights with `func` and set `bias` to 0."
    if func and hasattr(m, 'weight'): func(m.weight)
    with torch.no_grad():
        if getattr(m, 'bias', None) is not None: m.bias.fill_(0.)
    return m

#Cell
def _conv_func(ndim=2, transpose=False):
    "Return the proper conv `ndim` function, potentially `transposed`."
    assert 1 <= ndim <=3
    return getattr(nn, f'Conv{"Transpose" if transpose else ""}{ndim}d')

#Cell
defaults.activation=nn.ReLU

#Cell
class ConvLayer(nn.Sequential):
    "Create a sequence of convolutional (`ni` to `nf`), ReLU (if `use_activ`) and `norm_type` layers."
    def __init__(self, ni, nf, ks=3, stride=1, padding=None, bias=None, ndim=2, norm_type=NormType.Batch, bn_1st=True,
                 act_cls=defaults.activation, transpose=False, init=nn.init.kaiming_normal_, xtra=None, **kwargs):
        if padding is None: padding = ((ks-1)//2 if not transpose else 0)
        bn = norm_type in (NormType.Batch, NormType.BatchZero)
        if bias is None: bias = not bn
        conv_func = _conv_func(ndim, transpose=transpose)
        conv = init_default(conv_func(ni, nf, kernel_size=ks, bias=bias, stride=stride, padding=padding, **kwargs), init)
        if   norm_type==NormType.Weight:   conv = weight_norm(conv)
        elif norm_type==NormType.Spectral: conv = spectral_norm(conv)
        layers = [conv]
        act_bn = []
        if act_cls is not None: act_bn.append(act_cls())
        if bn: act_bn.append(BatchNorm(nf, norm_type=norm_type, ndim=ndim))
        if bn_1st: act_bn.reverse()
        layers += act_bn
        if xtra: layers.append(xtra)
        super().__init__(*layers)

#Cell
def AdaptiveAvgPool(sz=1, ndim=2):
    "nn.AdaptiveAvgPool layer for `ndim`"
    assert 1 <= ndim <= 3
    return getattr(nn, f"AdaptiveAvgPool{ndim}d")(sz)

#Cell
def MaxPool(ks=2, stride=None, padding=0, ndim=2):
    "nn.MaxPool layer for `ndim`"
    assert 1 <= ndim <= 3
    return getattr(nn, f"MaxPool{ndim}d")(ks, stride=stride, padding=padding)

#Cell
def AvgPool(ks=2, stride=None, padding=0, ndim=2, ceil_mode=False):
    "nn.AvgPool layer for `ndim`"
    assert 1 <= ndim <= 3
    return getattr(nn, f"AvgPool{ndim}d")(ks, stride=stride, padding=padding, ceil_mode=ceil_mode)

#Cell
@funcs_kwargs
class BaseLoss():
    "Same as `loss_cls`, but flattens input and target."
    activation=decodes=noops
    _methods = "activation decodes".split()
    def __init__(self, loss_cls, *args, axis=-1, flatten=True, floatify=False, is_2d=True, **kwargs):
        store_attr(self, "axis,flatten,floatify,is_2d")
        self.func = loss_cls(*args,**kwargs)
        functools.update_wrapper(self, self.func)

    def __repr__(self): return f"FlattenedLoss of {self.func}"
    @property
    def reduction(self): return self.func.reduction
    @reduction.setter
    def reduction(self, v): self.func.reduction = v

    def __call__(self, inp, targ, **kwargs):
        inp  = inp .transpose(self.axis,-1).contiguous()
        targ = targ.transpose(self.axis,-1).contiguous()
        if self.floatify and targ.dtype!=torch.float16: targ = targ.float()
        if targ.dtype in [torch.int8, torch.int16, torch.int32]: targ = targ.long()
        if self.flatten: inp = inp.view(-1,inp.shape[-1]) if self.is_2d else inp.view(-1)
        return self.func.__call__(inp, targ.view(-1) if self.flatten else targ, **kwargs)

#Cell
@delegates(keep=True)
class CrossEntropyLossFlat(BaseLoss):
    "Same as `nn.CrossEntropyLoss`, but flattens input and target."
    y_int = True
    def __init__(self, *args, axis=-1, **kwargs): super().__init__(nn.CrossEntropyLoss, *args, axis=axis, **kwargs)
    def decodes(self, x):    return x.argmax(dim=self.axis)
    def activation(self, x): return F.softmax(x, dim=self.axis)

#Cell
@delegates(keep=True)
class BCEWithLogitsLossFlat(BaseLoss):
    "Same as `nn.CrossEntropyLoss`, but flattens input and target."
    def __init__(self, *args, axis=-1, floatify=True, thresh=0.5, **kwargs):
        super().__init__(nn.BCEWithLogitsLoss, *args, axis=axis, floatify=floatify, is_2d=False, **kwargs)
        self.thresh = thresh

    def decodes(self, x):    return x>self.thresh
    def activation(self, x): return torch.sigmoid(x)

#Cell
def BCELossFlat(*args, axis=-1, floatify=True, **kwargs):
    "Same as `nn.BCELoss`, but flattens input and target."
    return BaseLoss(nn.BCELoss, *args, axis=axis, floatify=floatify, is_2d=False, **kwargs)

#Cell
def MSELossFlat(*args, axis=-1, floatify=True, **kwargs):
    "Same as `nn.MSELoss`, but flattens input and target."
    return BaseLoss(nn.MSELoss, *args, axis=axis, floatify=floatify, is_2d=False, **kwargs)

#Cell
class LabelSmoothingCrossEntropy(Module):
    y_int = True
    def __init__(self, eps:float=0.1, reduction='mean'): self.eps,self.reduction = eps,reduction

    def forward(self, output, target):
        c = output.size()[-1]
        log_preds = F.log_softmax(output, dim=-1)
        if self.reduction=='sum': loss = -log_preds.sum()
        else:
            loss = -log_preds.sum(dim=-1)
            if self.reduction=='mean':  loss = loss.mean()
        return loss*self.eps/c + (1-self.eps) * F.nll_loss(log_preds, target, reduction=self.reduction)

    def activation(self, out): return F.softmax(out, dim=-1)
    def decodes(self, out):    return out.argmax(dim=-1)

#Cell
def trunc_normal_(x, mean=0., std=1.):
    "Truncated normal initialization (approximation)"
    # From https://discuss.pytorch.org/t/implementing-truncated-normal-initializer/4778/12
    return x.normal_().fmod_(2).mul_(std).add_(mean)

#Cell
class Embedding(nn.Embedding):
    "Embedding layer with truncated normal initialization"
    def __init__(self, ni, nf):
        super().__init__(ni, nf)
        trunc_normal_(self.weight.data, std=0.01)

#Cell
class SelfAttention(nn.Module):
    "Self attention layer for `n_channels`."
    def __init__(self, n_channels):
        super().__init__()
        self.query,self.key,self.value = [self._conv(n_channels, c) for c in (n_channels//8,n_channels//8,n_channels)]
        self.gamma = nn.Parameter(tensor([0.]))

    def _conv(self,n_in,n_out):
        return ConvLayer(n_in, n_out, ks=1, ndim=1, norm_type=NormType.Spectral, act_cls=None, bias=False)

    def forward(self, x):
        #Notation from the paper.
        size = x.size()
        x = x.view(*size[:2],-1)
        f,g,h = self.query(x),self.key(x),self.value(x)
        beta = F.softmax(torch.bmm(f.transpose(1,2), g), dim=1)
        o = self.gamma * torch.bmm(h, beta) + x
        return o.view(*size).contiguous()

#Cell
class PooledSelfAttention2d(nn.Module):
    "Pooled self attention layer for 2d."
    def __init__(self, n_channels):
        super().__init__()
        self.n_channels = n_channels
        self.query,self.key,self.value = [self._conv(n_channels, c) for c in (n_channels//8,n_channels//8,n_channels//2)]
        self.out   = self._conv(n_channels//2, n_channels)
        self.gamma = nn.Parameter(tensor([0.]))

    def _conv(self,n_in,n_out):
        return ConvLayer(n_in, n_out, ks=1, norm_type=NormType.Spectral, act_cls=None, bias=False)

    def forward(self, x):
        n_ftrs = x.shape[2]*x.shape[3]
        f = self.query(x).view(-1, self.n_channels//8, n_ftrs)
        g = F.max_pool2d(self.key(x),   [2,2]).view(-1, self.n_channels//8, n_ftrs//4)
        h = F.max_pool2d(self.value(x), [2,2]).view(-1, self.n_channels//2, n_ftrs//4)
        beta = F.softmax(torch.bmm(f.transpose(1, 2), g), -1)
        o = self.out(torch.bmm(h, beta.transpose(1,2)).view(-1, self.n_channels//2, x.shape[2], x.shape[3]))
        return self.gamma * o + x

#Cell
def _conv1d_spect(ni:int, no:int, ks:int=1, stride:int=1, padding:int=0, bias:bool=False):
    "Create and initialize a `nn.Conv1d` layer with spectral normalization."
    conv = nn.Conv1d(ni, no, ks, stride=stride, padding=padding, bias=bias)
    nn.init.kaiming_normal_(conv.weight)
    if bias: conv.bias.data.zero_()
    return spectral_norm(conv)

#Cell
class SimpleSelfAttention(Module):
    def __init__(self, n_in:int, ks=1, sym=False):
        self.sym,self.n_in = sym,n_in
        self.conv = _conv1d_spect(n_in, n_in, ks, padding=ks//2, bias=False)
        self.gamma = nn.Parameter(tensor([0.]))

    def forward(self,x):
        if self.sym:
            c = self.conv.weight.view(self.n_in,self.n_in)
            c = (c + c.t())/2
            self.conv.weight = c.view(self.n_in,self.n_in,1)

        size = x.size()
        x = x.view(*size[:2],-1)

        convx = self.conv(x)
        xxT = torch.bmm(x,x.permute(0,2,1).contiguous())
        o = torch.bmm(xxT, convx)
        o = self.gamma * o + x
        return o.view(*size).contiguous()

#Cell
def icnr_init(x, scale=2, init=nn.init.kaiming_normal_):
    "ICNR init of `x`, with `scale` and `init` function"
    ni,nf,h,w = x.shape
    ni2 = int(ni/(scale**2))
    k = init(x.new_zeros([ni2,nf,h,w])).transpose(0, 1)
    k = k.contiguous().view(ni2, nf, -1)
    k = k.repeat(1, 1, scale**2)
    return k.contiguous().view([nf,ni,h,w]).transpose(0, 1)

#Cell
class PixelShuffle_ICNR(nn.Sequential):
    "Upsample by `scale` from `ni` filters to `nf` (default `ni`), using `nn.PixelShuffle`."
    def __init__(self, ni, nf=None, scale=2, blur=False, norm_type=NormType.Weight, act_cls=defaults.activation):
        super().__init__()
        nf = ifnone(nf, ni)
        layers = [ConvLayer(ni, nf*(scale**2), ks=1, norm_type=norm_type, act_cls=act_cls),
                  nn.PixelShuffle(scale)]
        layers[0][0].weight.data.copy_(icnr_init(layers[0][0].weight.data))
        if blur: layers += [nn.ReplicationPad2d((1,0,1,0)), nn.AvgPool2d(2, stride=1)]
        super().__init__(*layers)

#Cell
class SequentialEx(Module):
    "Like `nn.Sequential`, but with ModuleList semantics, and can access module input"
    def __init__(self, *layers): self.layers = nn.ModuleList(layers)

    def forward(self, x):
        res = x
        for l in self.layers:
            res.orig = x
            nres = l(res)
            # We have to remove res.orig to avoid hanging refs and therefore memory leaks
            res.orig = None
            res = nres
        return res

    def __getitem__(self,i): return self.layers[i]
    def append(self,l):      return self.layers.append(l)
    def extend(self,l):      return self.layers.extend(l)
    def insert(self,i,l):    return self.layers.insert(i,l)

#Cell
class MergeLayer(Module):
    "Merge a shortcut with the result of the module by adding them or concatenating them if `dense=True`."
    def __init__(self, dense:bool=False): self.dense=dense
    def forward(self, x): return torch.cat([x,x.orig], dim=1) if self.dense else (x+x.orig)

#Cell
class Cat(nn.ModuleList):
    "Concatenate layers outputs over a given dim"
    def __init__(self, layers, dim=1):
        self.dim=dim
        super().__init__(layers)
    def forward(self, x): return torch.cat([l(x) for l in self], dim=self.dim)

#Cell
class SimpleCNN(nn.Sequential):
    "Create a simple CNN with `filters`."
    def __init__(self, filters, kernel_szs=None, strides=None, bn=True):
        nl = len(filters)-1
        kernel_szs = ifnone(kernel_szs, [3]*nl)
        strides    = ifnone(strides   , [2]*nl)
        layers = [ConvLayer(filters[i], filters[i+1], kernel_szs[i], stride=strides[i],
                  norm_type=(NormType.Batch if bn and i<nl-1 else None)) for i in range(nl)]
        layers.append(PoolFlatten())
        super().__init__(*layers)

#Cell
class ResBlock(nn.Module):
    "Resnet block from `ni` to `nh` with `stride`"
    @delegates(ConvLayer.__init__)
    def __init__(self, expansion, ni, nh, stride=1, sa=False, sym=False,
                 norm_type=NormType.Batch, act_cls=defaults.activation, ndim=2, **kwargs):
        super().__init__()
        norm2 = NormType.BatchZero if norm_type==NormType.Batch else norm_type
        nf,ni = nh*expansion,ni*expansion
        layers  = [ConvLayer(ni, nh, 3, stride=stride, norm_type=norm_type, act_cls=act_cls, ndim=ndim, **kwargs),
                   ConvLayer(nh, nf, 3, norm_type=norm2, act_cls=None, ndim=ndim, **kwargs)
        ] if expansion == 1 else [
                   ConvLayer(ni, nh, 1, norm_type=norm_type, act_cls=act_cls, ndim=ndim, **kwargs),
                   ConvLayer(nh, nh, 3, stride=stride, norm_type=norm_type, act_cls=act_cls, ndim=ndim, **kwargs),
                   ConvLayer(nh, nf, 1, norm_type=norm2, act_cls=None, ndim=ndim, **kwargs)
        ]
        self.convs = nn.Sequential(*layers)
        self.sa = SimpleSelfAttention(nf,ks=1,sym=sym) if sa else noop
        self.idconv = noop if ni==nf else ConvLayer(ni, nf, 1, act_cls=None, ndim=ndim, **kwargs)
        self.pool = noop if stride==1 else AvgPool(2, ndim=ndim, ceil_mode=True)
        self.act = defaults.activation(inplace=True) if act_cls is defaults.activation else act_cls()

    def forward(self, x): return self.act(self.sa(self.convs(x)) + self.idconv(self.pool(x)))

#Cell
from torch.jit import script

@script
def _swish_jit_fwd(x): return x.mul(torch.sigmoid(x))

@script
def _swish_jit_bwd(x, grad_output):
    x_sigmoid = torch.sigmoid(x)
    return grad_output * (x_sigmoid * (1 + x * (1 - x_sigmoid)))

class _SwishJitAutoFn(torch.autograd.Function):
    @staticmethod
    def forward(ctx, x):
        ctx.save_for_backward(x)
        return _swish_jit_fwd(x)

    @staticmethod
    def backward(ctx, grad_output):
        x = ctx.saved_variables[0]
        return _swish_jit_bwd(x, grad_output)

#Cell
def swish(x, inplace=False): return _SwishJitAutoFn.apply(x)

#Cell
class Swish(Module):
    def forward(self, x): return _SwishJitAutoFn.apply(x)

#Cell
@script
def _mish_jit_fwd(x): return x.mul(torch.tanh(F.softplus(x)))

@script
def _mish_jit_bwd(x, grad_output):
    x_sigmoid = torch.sigmoid(x)
    x_tanh_sp = F.softplus(x).tanh()
    return grad_output.mul(x_tanh_sp + x * x_sigmoid * (1 - x_tanh_sp * x_tanh_sp))

class MishJitAutoFn(torch.autograd.Function):
    @staticmethod
    def forward(ctx, x):
        ctx.save_for_backward(x)
        return _mish_jit_fwd(x)

    @staticmethod
    def backward(ctx, grad_output):
        x = ctx.saved_variables[0]
        return _mish_jit_bwd(x, grad_output)

#Cell
def mish(x): return MishJitAutoFn.apply(x)

#Cell
class MishJit(Module):
    def forward(self, x): return MishJitAutoFn.apply(x)

#Cell
class ParameterModule(Module):
    "Register a lone parameter `p` in a module."
    def __init__(self, p): self.val = p
    def forward(self, x): return x

#Cell
def children_and_parameters(m):
    "Return the children of `m` and its direct parameters not registered in modules."
    children = list(m.children())
    children_p = sum([[id(p) for p in c.parameters()] for c in m.children()],[])
    for p in m.parameters():
        if id(p) not in children_p: children.append(ParameterModule(p))
    return children

#Cell
class TstModule(Module):
    def __init__(self): self.a,self.lin = nn.Parameter(torch.randn(1)),nn.Linear(5,10)

tst = TstModule()
children = children_and_parameters(tst)
test_eq(len(children), 2)
test_eq(children[0], tst.lin)
assert isinstance(children[1], ParameterModule)
test_eq(children[1].val, tst.a)

#Cell
def _has_children(m:nn.Module):
    try: next(m.children())
    except StopIteration: return False
    return True

nn.Module.has_children = property(_has_children)

#Cell
def flatten_model(m):
    "Return the list of all submodules and parameters of `m`"
    return sum(map(flatten_model,children_and_parameters(m)),[]) if m.has_children else [m]

#Cell
class NoneReduce():
    "A context manager to evaluate `loss_func` with none reduce."
    def __init__(self, loss_func): self.loss_func,self.old_red = loss_func,None

    def __enter__(self):
        if hasattr(self.loss_func, 'reduction'):
            self.old_red = self.loss_func.reduction
            self.loss_func.reduction = 'none'
            return self.loss_func
        else: return partial(self.loss_func, reduction='none')

    def __exit__(self, type, value, traceback):
        if self.old_red is not None: self.loss_func.reduction = self.old_red

#Cell
def in_channels(m):
    "Return the shape of the first weight layer in `m`."
    for l in flatten_model(m):
        if hasattr(l, 'weight'): return l.weight.shape[1]
    raise Exception('No weight layer')