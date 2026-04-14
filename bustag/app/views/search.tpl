% rebase('base.tpl', title='搜索', path=path)
<div class="container">
  <div class="row py-3">
    <div class="col-12">
      <form action="/search" method="get" class="form-inline justify-content-center">
        <div class="input-group" style="max-width: 400px;">
          <input type="text" name="q" class="form-control" placeholder="输入番号搜索，如 SSIS-001" value="{{query}}">
          <div class="input-group-append">
            <button class="btn btn-primary" type="submit">搜索</button>
          </div>
        </div>
      </form>
    </div>
  </div>

% if defined('item') and item is not None:
  <div class="row py-3">
    <div class="col-12 col-md-4">
      <img class="img-fluid img-thumbnail coverimg" src="/img_proxy?url={{item.cover_img_url}}">
    </div>
    <div class="col-12 col-md-8">
      <h5>{{item.fanhao}}</h5>
      <a href="{{item.url}}" target="_blank">{{item.title}}</a>
      <div class="small text-muted mt-2">发行日期: {{item.release_date}}</div>
      <div class="small text-muted">添加日期: {{item.add_date}}</div>
      <div class="mt-2">
      % for t in item.tags_dict.get('genre', []):
        <span class="badge badge-primary">{{t}}</span>
      % end
      </div>
      <div class="mt-1">
      % for t in item.tags_dict.get('star', []):
        <span class="badge badge-warning">{{t}}</span>
      % end
      </div>
    </div>
  </div>
% elif defined('query') and query != '':
  <div class="row py-3">
    <div class="col-12 text-center">
      <div class="alert alert-warning">未找到番号「{{query}}」的相关信息</div>
    </div>
  </div>
% end
</div>