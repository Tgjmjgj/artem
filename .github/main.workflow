workflow "New workflow" {
  on = "push"
  resolves = ["Python Style Checker"]
}

action "Python Style Checker" {
  uses = "andymckay/pycodestyle-action@0.1.3"
}
