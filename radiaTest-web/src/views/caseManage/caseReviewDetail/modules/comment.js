import { ref } from 'vue';
import { getCaseReviewComment } from '@/api/get';
import { createComment } from '@/api/post';
import router from '@/router';
const comments = ref([]);
const commentInput = ref('');
function getComment() {
  const commit = router.currentRoute.value.params.commitId;
  getCaseReviewComment(commit).then((res) => {
    comments.value = res.data;
  });
}
function commentCase() {
  createComment(router.currentRoute.value.params.commitId, {
    parent_id: 0,
    content: commentInput.value
  }).then(() => {
    commentInput.value = '';
    getComment();
  });
}
export { comments, commentInput, getComment, commentCase };
