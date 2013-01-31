/*
 * Copyright 2013 Red Hat Inc., Durham, North Carolina.
 * All Rights Reserved.
 *
 * This program is free software: you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation, either version 3 of the License, or
 * (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with this program.  If not, see <http://www.gnu.org/licenses/>.
 *
 * Authors:
 *      Martin Preisler <mpreisle@redhat.com>
 */

#include "ForwardDecls.h"

#include "Evaluator.h"
#include <QStringList>
#include <QProcess>

class OscapEvaluatorBase : public Evaluator
{
    Q_OBJECT

    public:
        OscapEvaluatorBase(QThread* thread, struct xccdf_session* session, const QString& target);
        virtual ~OscapEvaluatorBase();

    protected:
        QStringList buildCommandLineArgs(const QString& inputFile, const QString& resultFile);
};

class OscapEvaluatorLocal : public OscapEvaluatorBase
{
    Q_OBJECT

    public:
        OscapEvaluatorLocal(QThread* thread, struct xccdf_session* session, const QString& target);
        virtual ~OscapEvaluatorLocal();

        virtual void evaluate();
        virtual void cancel();

    private:
        bool tryToReadLine(QProcess& process);

        bool mCancelRequested;
};
