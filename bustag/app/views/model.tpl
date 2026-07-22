% rebase('base.tpl', title='模型管理', path=path)

<div class="container">
 <div class="row py-3">
 <div class="col-10 offset-1 ">
    <div class="accordion" id="accordionExample">
  <div class="card">
    <div class="card-header" id="headingOne">
      <h2 class="mb-0">
        <button class="btn btn-link" type="button" data-toggle="collapse" data-target="#collapseOne" aria-expanded="true" aria-controls="collapseOne">
          训练模型
        </button>
      </h2>
    </div>

    <div id="collapseOne" class="collapse show" aria-labelledby="headingOne" data-parent="#accordionExample">
        <div class="card-body">
        <h5 class="card-title">重新训练模型</h5>
        <p class="card-text">重新使用系统所有用户打标数据训练模型, 当打标数据增多后, 可以重新训练模型, 提高模型预测效果</p>
        <a href="/do-training" class="btn btn-primary">开始训练</a>

        <hr class="my-3">
        <h6 class="card-title">推荐数据管理</h6>
        <p class="card-text text-muted">训练新模型后，旧推荐结果不会自动更新。可在此清理旧推荐，再用当前模型重新生成推荐。</p>
        <button type="button" id="btn-clear-recommend" class="btn btn-warning">清理旧推荐</button>
        <button type="button" id="btn-re-recommend" class="btn btn-success">重新推荐</button>
        <div id="recommend-result" class="mt-2 text-muted small"></div>
        </div>
        <div class="card-header">
           <h6> 当前模型数据 </h6>
        </div>
        % if defined('error_msg') and error_msg is not None:
        <p class="card-text text-danger">{{error_msg}} </a>
        % end
        % if model_scores is not None:
        <ul class="list-group list-group-flush">
            <li class="list-group-item">准确率 (Precision): {{model_scores.get('precision', 'N/A')}}</li>
            <li class="list-group-item">覆盖率 (Recall): {{model_scores.get('recall', 'N/A')}}</li>
            <li class="list-group-item">综合评分 F1 (越高越好): {{model_scores.get('f1', 'N/A')}}</li>
            % if 'auc' in model_scores:
            <li class="list-group-item">AUC 区分度 (越接近1越好): {{model_scores['auc']}}</li>
            % end
            % if 'cv_f1_mean' in model_scores:
            <li class="list-group-item">5折交叉验证 F1: {{model_scores['cv_f1_mean']}} ± {{model_scores['cv_f1_std']}}</li>
            % end
        </ul>
        % if 'top_features' in model_scores and model_scores['top_features']:
        <div class="card-header mt-2">
           <h6> Top 10 重要特征 </h6>
        </div>
        <ul class="list-group list-group-flush">
            % for feat_name, feat_imp in model_scores['top_features']:
            <li class="list-group-item d-flex justify-content-between align-items-center">
                {{feat_name}}
                <span class="badge badge-primary badge-pill">{{feat_imp}}</span>
            </li>
            % end
        </ul>
        % end
        % else:
        <div class="card-body">
           还没有训练过模型.
        </div>
        % end
        </div>
    </div>
  </div>
  <div class="card">
    <div class="card-header" id="headingTwo">
      <h2 class="mb-0">
        <button class="btn btn-link collapsed" type="button" data-toggle="collapse" data-target="#collapseTwo" aria-expanded="false" aria-controls="collapseTwo">
          优化说明
        </button>
      </h2>
    </div>
    <div id="collapseTwo" class="collapse" aria-labelledby="headingTwo" data-parent="#accordionExample">
      <div class="card-body">
        <h6>特征工程优化</h6>
        <ul>
            <li>按标签类型（genre/star/other）分别编码，而非混合编码</li>
            <li>新增数值特征：标签数量、演员数量、是否有演员信息</li>
            <li>新增系列（番号前缀）特征</li>
        </ul>
        <h6>模型优化</h6>
        <ul>
            <li>LightGBM 梯度提升树，更多树 + 更低学习率</li>
            <li>5折交叉验证评估模型稳定性</li>
            <li>AUC 指标评估模型区分能力</li>
            <li>概率阈值推荐（≥0.6 才推荐），减少误推荐</li>
        </ul>
      </div>
    </div>
  </div>
 </div>
 </div>
</div>
</div>