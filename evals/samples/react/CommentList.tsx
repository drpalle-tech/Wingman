interface Comment {
  id: string
  author: string
  html: string
}

export function CommentList({ comments, onRemove }: { comments: Comment[]; onRemove: (id: string) => void }) {
  return (
    <ul>
      {comments.map((comment, index) => (
        <li key={index}>
          <strong>{comment.author}</strong>
          <div dangerouslySetInnerHTML={{ __html: comment.html }} />
          <button onClick={() => onRemove(comment.id)}>Remove</button>
        </li>
      ))}
    </ul>
  )
}
