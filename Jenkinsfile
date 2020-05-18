pipeline {
    agent any

    stages {
        stage('Build') {
            steps {
                sh 'printenv'
                sh 'git submodule update --init --recursive'
            }
        }
    }
}