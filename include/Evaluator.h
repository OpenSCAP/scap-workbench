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

#include <QObject>

extern "C"
{
#include <xccdf_benchmark.h>
}

class Evaluator : public QObject
{
    Q_OBJECT

    public:
        Evaluator(QThread* thread, struct xccdf_session* session, const QString& target);
        virtual ~Evaluator();

    public slots:
        virtual void evaluate() = 0;
        virtual void cancel() = 0;

    signals:
        void progressReport(const QString& rule_id, xccdf_test_result_type_t result);
        void canceled();
        void finished();

    protected:
        QThread* mThread;
        struct xccdf_session* mSession;
        const QString mTarget;

        void signalCompletion(bool canceled);
};
