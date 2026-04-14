% curr_page = page_info[2]
% max_page = page_info[1]
% total_items = page_info[0]
% setdefault('like', '')
% like_param = '&like={}'.format(like) if like is not None and like != '' else ''
<div class="row">
	<div class="col-12 text-center">
	<h6>
	% if curr_page != 1:
	<a href="?page=1{{like_param}}"> 第一页</a>
	% end
	% if curr_page > 1:
	<a href="?page={{curr_page - 1}}{{like_param}}"> 上一页</a>
	% end
	第{{curr_page}}页
	% if curr_page < max_page:
	 <a href="?page={{curr_page + 1}}{{like_param}}">下一页</a>
	% end
	% if curr_page != max_page:
	<a href="?page={{max_page}}{{like_param}}">最后页</a>
	% end
	</h6>
	<div>
	<form>
		<span>共  {{max_page}}页,{{total_items}}条</span>
	跳转
	<select id="pagenav">
% for i in range(1, max_page+1):
% url = '?page={}{}'.format(i, like_param)
% selected = "selected" if i == curr_page else ""
	<option {{selected}} value="{{url}}">{{i}}</option>
% end
	</select>
	页
	</form>
	</div>
	</div>
</div>
